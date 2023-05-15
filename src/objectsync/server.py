from typing import Dict, TypeVar
import uuid
from chatroom import ChatroomServer, Transition
from chatroom.topic import Topic, IntTopic, SetTopic, DictTopic
from chatroom.change import EventChangeTypes, StringChangeTypes

from objectsync.hierarchy_utils import get_ancestors, lowest_common_ancestor
from objectsync.history import HistoryItem
from objectsync.sobject import SObject, SObjectSerialized

class Server:
    def __init__(self, port: int, host:str='localhost', root_object_type:type[SObject]=SObject) -> None:
        self._port = port
        self._host = host
        self._chatroom = ChatroomServer(port,host,on_transition_done=self._on_transition_done)
        self._objects : Dict[str,SObject] = {}
        root_id = 'root'
        self._root_object = root_object_type(self,root_id,'')
        self._objects[root_id] = self._root_object
        self._objects_topic = self.create_topic('_objects',DictTopic,{root_id:'root'})
        self._object_types : Dict[str,type[SObject]] = {}

        # Link callbacks to chatroom events
        # so these mehtods can be called from both client and server
        self._chatroom.on('create_object', self._create_object, self._destroy_object)
        self._chatroom.on('destroy_object', self._destroy_object, self._create_object)

        self._chatroom.register_service('undo', self._undo)
        self._chatroom.register_service('redo', self._redo)

        self.record = self._chatroom.record
        '''Use this context manager to package multiple changes into a single transition to create resonable undo/redo behavior'''

    async def serve(self):
        '''
        Entry point for the server
        '''
        await self._chatroom.serve()

    '''
    Callbacks
    '''

    def _create_object(self, type: str, parent_id, id:str|None=None, serialized:SObjectSerialized|None=None):
        print(f'create object: {type} {id}')
        if id is None:
            id = str(uuid.uuid4())
        cls = self._object_types[type]
        self._objects_topic.add(id,cls.frontend_type)
        new_object = cls(self,id,parent_id)
        self._objects[id] = new_object
        new_object.get_parent()._add_child(new_object)
        assert new_object.get_parent().get_id() == parent_id
        new_object.initialize(serialized)
        return {'id':id,'type':type,'parent_id':parent_id,'serialized':new_object.serialize()}
    
    def _destroy_object(self, id, **kwargs):
        self._objects_topic.remove(id)
        obj = self._objects[id]
        serialized = obj.destroy()
        obj.get_parent()._remove_child(obj)
        del self._objects[id]
        return {'type':obj.__class__.__name__,'parent_id':obj.get_parent().get_id(),'serialized':serialized}
    
    def _on_transition_done(self, transition:Transition):
        # Find the lowest object to record the transition in
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

        if len(affected_objs) == 0:
            return

        lowest = lowest_common_ancestor(affected_objs)
        for obj in get_ancestors(lowest):
            obj.history.add(transition)
        print('\n=== tran ===')
        for change in transition.changes:
            print(change.serialize())
        print('')

    def _undo(self, target = None):
        if target is None:
            target = 'root'
        transition = self._objects[target].history.undo()

        if transition is not None:
            self._chatroom.undo(transition)
        else:
            print('no transition to undo')

    def _redo(self, target = None):
        if target is None:
            target = 'root'
        transition = self._objects[target].history.redo()
        if transition is not None:
            self._chatroom.redo(transition)
        else:
            print('no transition to redo')

    '''
    Basic methods
    '''

    def add_object_type(self, object_type:type[SObject]):
        self._object_types[object_type.__name__] = object_type

    def get_object(self, id:str) -> SObject:
        return self._objects[id]
    
    def create_object_s(self, type:str, parent_id:str, id:str|None = None, serialized:SObjectSerialized|None=None) -> SObject:
        if id is None:
            id = uuid.uuid4().hex
        self._chatroom.emit('create_object', type = type, parent_id = parent_id, id = id, serialized = serialized)
        return self.get_object(id)
    
    T=TypeVar('T', bound=SObject)
    def create_object(self, type:type[T], parent_id:str, id:str|None = None, serialized:SObjectSerialized|None=None) -> T:
        new_object = self.create_object_s(type.__name__, parent_id, id, serialized)
        assert isinstance(new_object, type)
        return new_object
    
    def destroy_object(self, id:str):
        self._chatroom.emit('destroy_object', id = id)

    '''
    Encapsulate the chatroom server
    '''

    T = TypeVar('T', bound=Topic)
    def create_topic(self, topic_name, topic_type: type[T],init_value=None) -> T:
        topic = self._chatroom.add_topic(topic_name,topic_type,init_value)
        return topic

    T = TypeVar('T', bound=Topic)
    def get_topic(self, topic_name, type: type[T]) -> T:
        return self._chatroom.topic(topic_name,type)
    
    def remove_topic(self, topic_name):
        self._chatroom.remove_topic(topic_name)
