import logging

from objectsync.utils import NameSpace
logger = logging.getLogger(__name__)
from typing import Dict, List, TypeVar, Any, Callable
from chatroom import ChatroomServer, Transition
from chatroom.topic import Topic, IntTopic, SetTopic, DictTopic
from chatroom.change import EventChangeTypes, StringChangeTypes

from objectsync.hierarchy_utils import get_ancestors, lowest_common_ancestor
from objectsync.count import gen_id, get_id_count, set_id_count
from objectsync.sobject import SObject, SObjectSerialized

class Server:
    def __init__(self, port: int, host:str='localhost', root_object_type:type[SObject]=SObject) -> None:
        self._port = port
        self._host = host
        self._chatroom = ChatroomServer(port,host,transition_callback=self._transition_callback)
        self._objects : Dict[str,SObject] = {}
        root_id = 'root'
        self._root_object = root_object_type(self,root_id,'')
        self._objects[root_id] = self._root_object
        self._objects_topic = self.create_topic('_objects',DictTopic,{root_id:'Root'})
        self._object_types : Dict[str,type[SObject]] = {}
        self._object_types_to_names : Dict[type[SObject],str] = {SObject:'SObject'}

        # Link callbacks to chatroom events
        # so these methods can be called from both client and server
        self._chatroom.on('create_object', self._create_object, self._destroy_object)
        self._chatroom.on('destroy_object', self._destroy_object, self._create_object)

        self._chatroom.register_service('undo', self._undo)
        self._chatroom.register_service('redo', self._redo)

        self.register_service = self._chatroom.register_service

        self.record = self._chatroom.record
        '''Use this context manager to package multiple changes into a single transition to create resonable undo/redo behavior'''
        self.set_client_id_count = self._chatroom.set_client_id_count
        self.get_client_id_count = self._chatroom.get_client_id_count

        self.do_after_transition = self._chatroom.do_after_transition

        self.globals = NameSpace()
        
    async def serve(self):
        '''
        Entry point for the server
        '''
        await self._chatroom.serve()

    '''
    Callbacks
    '''

    def _create_object(self, type: str, parent_id, id:str|None=None, serialized:SObjectSerialized|None=None, build_kwargs:Dict[str,Any]={}):
        '''
        This method is "raw" create object. It does not record the creation in a transition.
        To create an object and record the creation in a transition, use create_object or create_object_s.
        '''
        logger.debug(f'create object: {type} {id}')
        if id is None:
            id = gen_id()
        cls = self._object_types[type]
        new_object = cls(self,id,parent_id)
        self._objects[id] = new_object
        new_object.initialize(serialized,build_kwargs=build_kwargs,call_init=False)
        temp = new_object.serialize()
        new_object.get_parent()._add_child(new_object)
        assert new_object.get_parent().get_id() == parent_id
        self._objects_topic.add(id,cls.frontend_type)
        new_object.init()
        return {'id':id,'type':type,'parent_id':parent_id,'serialized':temp}
    
    def _destroy_object(self, id, **kwargs):
        self._objects_topic.remove(id)
        obj = self._objects[id]
        serialized = obj.destroy()

        # Normally, obj should be in the parent's children list, but if the _destroy_object is called due to 
        # a failure in obj.initialize (which is called in _create_object), then the parent will not have the child.
        # Check if the parent has the child before removing it to avoid error.
        if obj.get_parent().has_child(obj):
            obj.get_parent()._remove_child(obj)

        del self._objects[id]
        return {'type':self._object_types_to_names[obj.__class__],'parent_id':obj.get_parent().get_id(),'serialized':serialized}
    
    def _transition_callback(self, transition:Transition):
        # Find the lowest object to record the transition in

        debug_msg = '\n=== tran ==='
        for change in transition.changes:
            debug_msg += '\n' + str(change.serialize())
        debug_msg += '\n'
        logger.debug(debug_msg)
        
        affected_objs = []
        for change in transition.changes:
            split = change.topic_name.split('/')
            match split[0]:
                case 'create_object':
                    assert isinstance(change, (EventChangeTypes.EmitChange))
                    affected_objs.append(self._objects[change.args['parent_id']])
                case 'destroy_object':
                    assert isinstance(change, (EventChangeTypes.EmitChange))
                    affected_objs.append(self._objects[change.forward_info['parent_id']])
                case 'a':
                    affected_objs.append(self._objects[split[1]])
                case 'parent_id':
                    assert isinstance(change, (StringChangeTypes.SetChange))
                    assert change.old_value is not None
                    affected_objs.append(self._objects[change.old_value])
                    affected_objs.append(self._objects[change.value])
                case 'tags':
                    affected_objs.append(self._objects[change.topic_name.split('/')[1]]) # improve this

        if len(affected_objs) == 0:
            return

        lowest = lowest_common_ancestor(affected_objs)
        for obj in get_ancestors(lowest):
            obj.history.add(transition)
        

    def _undo(self, target = None):
        if target is None:
            target = 'root'
        transition = self._objects[target].history.undo()

        if transition is not None:
            self._chatroom.undo(transition)
        else:
            logger.debug('no transition to undo')

    def _redo(self, target = None):
        if target is None:
            target = 'root'
        transition = self._objects[target].history.redo()
        if transition is not None:
            self._chatroom.redo(transition)
        else:
            logger.debug('no transition to redo')

    '''
    Basic methods
    '''

    def register(self, object_type:type[SObject],name:str|None=None):
        if name is None:
            name = object_type.__name__
        if self._object_types.get(name) is not None:
            raise ValueError(f'Object type {name} already exists')
        if self._object_types_to_names.get(object_type) is not None:
            raise ValueError(f'Object type {object_type} already exists')
        self._object_types[name] = object_type
        self._object_types_to_names[object_type] = name

    def unregister(self, object_type:type[SObject]|str):
        
        if isinstance(object_type,str):
            object_type_name = object_type
            object_type = self._object_types[object_type]

        else:
            object_type_name = self._object_types_to_names[object_type]

        # check if exists object of this type
        for obj in self._objects.values():
            if obj.get_type_name() == object_type_name:
                raise ValueError(f'Cannot unregister object type {self._object_types_to_names[object_type]} with existing object {obj.get_id()}')
        del self._object_types[object_type_name]
        del self._object_types_to_names[object_type]

    def get_all_node_types(self)->Dict[str,type[SObject]]:
        return self._object_types.copy()

    def get_object(self, id:str) -> SObject:
        return self._objects[id]
    
    def get_objects(self) -> List[SObject]:
        return list(self._objects.values())
    
    def create_object_s(self, type:str, parent_id:str, id:str|None = None, serialized:SObjectSerialized|None=None,**build_kwargs) -> SObject:
        if id is None:
            id = gen_id()
        self._chatroom.emit('create_object', type = type, parent_id = parent_id, id = id, serialized = serialized, build_kwargs=build_kwargs)
        return self.get_object(id)
    
    T=TypeVar('T', bound=SObject)
    def create_object(self, type:type[T], parent_id:str='root', id:str|None = None, serialized:SObjectSerialized|None=None,**build_kwargs) -> T:
        new_object = self.create_object_s(self._object_types_to_names[type], parent_id, id, serialized, **build_kwargs)
        assert isinstance(new_object, type)
        return new_object
    
    def destroy_object(self, id:str):
        self._chatroom.emit('destroy_object', id = id)

    def set_id_count(self, count:int):
        set_id_count(count)

    def get_id_count(self):
        return get_id_count()
    
    def get_object_type(self, name:str) -> type[SObject]:
        return self._object_types[name]
    
    def get_object_type_name(self, type:type[SObject]) -> str:
        return self._object_types_to_names[type]
    
    def get_root_object(self) -> SObject:
        return self._objects['root']

    '''
    Encapsulate the chatroom server
    '''

    T = TypeVar('T', bound=Topic)
    def create_topic(self, topic_name, topic_type: type[T],init_value=None,is_stateful=True) -> T:
        topic = self._chatroom.add_topic(topic_name,topic_type,init_value,is_stateful=is_stateful)
        return topic

    T = TypeVar('T', bound=Topic)
    def get_topic(self, topic_name, type: type[T]=Topic) -> T:
        return self._chatroom.topic(topic_name,type)
    
    def remove_topic(self, topic_name):
        self._chatroom.remove_topic(topic_name)

    def on(self, event_name: str, callback: Callable, inverse_callback: Callable|None = None, is_stateful: bool = True,auto=False, *args, **kwargs: None):
        self._chatroom.on(event_name, callback, inverse_callback, is_stateful,auto=auto)

    def emit(self, event_name, **kwargs):
        self._chatroom.emit(event_name, **kwargs)
