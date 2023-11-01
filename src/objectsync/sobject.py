from __future__ import annotations
import logging

from objectsync.utils import snake_to_camel
logger = logging.getLogger(__name__)
from dataclasses import dataclass
from mimetypes import init
from typing import List, Dict, Any, Optional, Self, TypeVar, Union, TYPE_CHECKING, Callable
import typing
from topicsync.topic import SetTopic, Topic, IntTopic, StringTopic, DictTopic, ListTopic, EventTopic, FloatTopic, GenericTopic
from objectsync.topic import ObjDictTopic, ObjListTopic, ObjSetTopic, ObjTopic, WrappedTopic

from objectsync.history import History, HistoryItem
from objectsync.count import gen_id

if TYPE_CHECKING:
    from objectsync.server import Server

@dataclass
class SObjectSerialized:
    id:str
    type:str
    attributes:List[List] # name, type, value, is_stateful
    children:Dict[str,SObjectSerialized]
    user_attribute_references:Dict[str,str]
    user_sobject_references:Dict[str,str]
    
    def to_dict(self):
        return {
            'id':self.id,
            'type':self.type,
            'attributes':self.attributes,
            'children':{child_id:child.to_dict() for child_id,child in self.children.items()},
            'user_attribute_references':self.user_attribute_references,
            'user_sobject_references':self.user_sobject_references,
        }

    def __dict__(self):
        return self.to_dict()

class SObject:
    frontend_type = 'Root'

    '''
    Initialization
    '''
    def __init__(self, server:Server, id:str, parent_id:str):
        self._server = server
        self._id = id
        self._parent_id = self._server.create_topic(f"parent_id/{id}", StringTopic, parent_id)
        self._tags = self._server.create_topic(f"tags/{id}", SetTopic, is_stateful=False)
        self._parent_id.on_set2 += self._on_parent_changed
        self._attributes : Dict[str,Topic|WrappedTopic] = {}
        self._children : List[SObject] = []
        self.history : History = History()
        self._destroyed = False

    def initialize(self, serialized:SObjectSerialized|None=None,build_kwargs:Dict[str,Any]={},call_init:bool=True):
        self.is_new = serialized is None
        if serialized is None:
            self.build(**build_kwargs)

            # collect attributes and sobjects references
            self._user_attribute_references = {}
            self._user_sobject_references = {}
            for k, v in self.__dict__.items():
                if isinstance(v, Topic|WrappedTopic):
                    if not v in self._attributes.values():
                        continue
                    self._user_attribute_references[k] = v.get_name().split('/')[-1]
                elif isinstance(v, SObject):
                    self._user_sobject_references[k] = v.get_id()
        else:
            self._deserialize(serialized)
        
        if call_init:
            self.init()

    def build(self,**kwargs):
        '''
        Create child objects and add attributes here.
        Notice: This method will not be called when the object is being restored.
        '''

    def _deserialize(self, serialized:SObjectSerialized):

        # restore attributes
        for name, type_name, value, is_stateful in serialized.attributes:
            # the type_name is a string, so we need to convert it to a type object
            full_type_name = snake_to_camel(type_name)+'Topic'
            full_type_name = full_type_name[0].upper() + full_type_name[1:]
            # grab the type from the air. Hacker.
            type = globals()[full_type_name]
            
            self.add_attribute(name, type, value, is_stateful)

        # restore attribute references used in user code
        for ref_name, attr_name in serialized.user_attribute_references.items():
            if getattr(self, ref_name, None) is not None:
                continue
            assert attr_name in self._attributes, f"Attribute {attr_name} not found in {self.get_id()} {self.get_type_name()}"
            setattr(self, ref_name, self._attributes[attr_name])

        # sort by child id so the creation order is the same as that specified in build()
        
        children = sorted(serialized.children.values(), key=self._server.deserialize_sort_key)
        for child_serialized in children:
            self._server._create_object(child_serialized.type, self._id, child_serialized.id, child_serialized)

        # restore sobject references added during build()
        for ref_name, sobject_id in serialized.user_sobject_references.items():
            if getattr(self, ref_name, None) is not None:
                continue
            setattr(self, ref_name, self._server.get_object(sobject_id))

        # remember these in case we need to serialize this object again
        self._user_attribute_references = serialized.user_attribute_references
        self._user_sobject_references = serialized.user_sobject_references

    def init(self):
        '''
        Called after the object and its children have been initialized.
        Link attributes to child objects, etc.
        '''

    '''
    Callbacks
    '''
    def _on_parent_changed(self, old_parent_id, new_parent_id):
        self._server.get_object(old_parent_id)._remove_child(self)
        self._server.get_object(new_parent_id)._add_child(self)

    '''
    Non API methods
    '''
    
    def _add_child(self, child:SObject):
        logger.debug(f"Adding child {child.get_id()} to {self.get_id()}")
        for c in self._children:
            if c.get_id() == child.get_id():
                raise ValueError(f"Child {child.get_id()} already exists")
        self._children.append(child)
    
    def _remove_child(self, child:SObject):
        logger.debug(f"Removing child {child.get_id()} from {self.get_id()}")
        self._children.remove(child)

    '''
    Public methods
    '''
    
    def get_id(self):
        return self._id
    
    def is_root(self):
        return self._id == 'root'

    T = TypeVar("T", bound='SObject')
    def add_child(self, type: type[T], **build_kwargs) -> T:
        id = gen_id()
        self._server.create_object(type, self._id, id=id, **build_kwargs)
        new_child = self._server.get_object(id)
        assert isinstance(new_child, type)
        return new_child
    
    def add_child_s(self,type:str,**build_kwargs) -> SObject:
        id = gen_id()
        self._server.create_object_s(type, self._id, id=id, **build_kwargs)
        new_child = self._server.get_object(id)
        return new_child
    
    def remove_child(self, child:SObject): # Maybe deprecate this
        self._server.destroy_object(child.get_id())
    
    def get_parent(self):
        if self._id == 'root':
            raise NotImplementedError('Cannot call get_parent of root object')
        return self._server.get_object(self._parent_id.get())
    
    T1 = TypeVar("T1", bound=Topic|WrappedTopic)
    def add_attribute(self, topic_name, topic_type: type[T1], init_value=None, is_stateful=True) -> T1: 
        origin_type = typing.get_origin(topic_type)
        if origin_type is None:
            origin_type = topic_type
        if topic_name in self._attributes:
            raise ValueError(f"Attribute '{topic_name}' already exists")
        def map_id_to_object(id):
            if self._server.has_object(id):
                return self._server.get_object(id)
            else:
                return None
        if origin_type == ObjTopic:
            if init_value is not None and isinstance(init_value, SObject):
                init_value = init_value.get_id()
            inner = self.add_attribute(topic_name, StringTopic, init_value, is_stateful)
            new_attr = ObjTopic(inner, map_id_to_object)
        elif origin_type == ObjDictTopic:
            if init_value is not None:
                assert isinstance(init_value, Dict)
                if len(init_value)>0 and isinstance(list(init_value.values())[0], SObject):
                    init_value = {key: value.get_id() for key, value in init_value.items()}
            inner = self.add_attribute(topic_name, DictTopic, init_value, is_stateful)
            new_attr = ObjDictTopic(inner, map_id_to_object)
        elif origin_type == ObjListTopic:
            if init_value is not None:
                assert isinstance(init_value, list)
                if len(init_value)>0 and isinstance(init_value[0], SObject):
                    init_value = [value.get_id() for value in init_value]
            inner = self.add_attribute(topic_name, ListTopic, init_value, is_stateful)
            new_attr = ObjListTopic(inner, map_id_to_object)
        elif origin_type == ObjSetTopic:
            if init_value is not None:
                assert isinstance(init_value, list)
                if len(init_value)>0 and isinstance(init_value[0], SObject):
                    init_value = [value.get_id() for value in init_value]
            inner = self.add_attribute(topic_name, SetTopic, init_value, is_stateful)
            new_attr = ObjSetTopic(inner, map_id_to_object)
        else:
            new_attr = self._server.create_topic(f"a/{self._id}/{topic_name}", topic_type, init_value, is_stateful) # type: ignore
        self._attributes[topic_name] = new_attr
        return new_attr # type: ignore
    
    def remove_attribute(self, topic_name):
        if topic_name not in self._attributes:
            raise ValueError(f"Attribute '{topic_name}' does not exist")
        self._server.remove_topic(self._attributes[topic_name].get_name())
        del self._attributes[topic_name]
    
    def get_attribute(self, topic_name) -> Topic|WrappedTopic:
        if topic_name not in self._attributes:
            raise ValueError(f"Attribute '{topic_name}' does not exist")
        return self._attributes[topic_name]
    
    def has_attribute(self, topic_name):
        return topic_name in self._attributes
    
    def emit(self, event_name, **kwargs):
        self._server.emit(f"a/{self._id}/{event_name}", **kwargs)
        if event_name not in self._attributes:
            self._attributes[event_name] = self._server.get_topic(f"a/{self._id}/{event_name}")
    
    def on(self, event_name: str, callback: Callable, inverse_callback: Callable|None = None, is_stateful: bool = True,auto=False):
        self._server.on(f"a/{self._id}/{event_name}", callback, inverse_callback, is_stateful,auto=auto)
        if event_name not in self._attributes:
            self._attributes[event_name] = self._server.get_topic(f"a/{self._id}/{event_name}")

    def register_service(self, service_name: str, callback: Callable, pass_sender: bool = False):
        self._server.register_service(f"{self._id}/{service_name}", callback, pass_sender)

    def remove(self):
        self._server.destroy_object(self._id)
    
    def destroy(self)-> SObjectSerialized:
        '''
        Caution: Do not call this method directly. Use remove() instead.
        '''
        if self._destroyed:
            raise ValueError(f"Object {self._id} already destroyed")
            
        self._destroyed = True

        self._server.remove_topic(self._parent_id.get_name())
        self._server.remove_topic(self._tags.get_name())

        attributes_serialized = []
        for name, attr in self._attributes.items():
            if isinstance(attr, WrappedTopic):
                value = attr.get_raw()
            else:
                value = attr.get()
            attributes_serialized.append([name,attr.get_type_name(),value,attr.is_stateful()])
            self._server.remove_topic(attr.get_name())

        children_serialized = {}
        for child in self._children.copy():
            logger.debug(f"Destroying child {child.get_id()} from {self.get_id()}")
            child_info = self._server._destroy_object(child.get_id())
            children_serialized[child.get_id()] = child_info['serialized']

        return SObjectSerialized(
            id = self._id,
            type = self._server.get_object_type_name(self.__class__),
            attributes = attributes_serialized,
            children = children_serialized,
            user_attribute_references=self._user_attribute_references,
            user_sobject_references=self._user_sobject_references
        )

    def is_destroyed(self):
        return self._destroyed
    
    def serialize(self) -> SObjectSerialized:

        attributes_serialized = []
        for name, attr in self._attributes.items():
            if isinstance(attr, WrappedTopic):
                value = attr.get_raw()
            else:
                value = attr.get()
            attributes_serialized.append([name,attr.get_type_name(),value,attr.is_stateful()])

        children_serialized = {child.get_id(): child.serialize() for child in self._children}
        return SObjectSerialized(
            id = self._id,
            type = self._server.get_object_type_name(self.__class__),
            attributes = attributes_serialized,
            children = children_serialized,
            user_attribute_references=self._user_attribute_references,
            user_sobject_references=self._user_sobject_references
        )

    def add_tag(self, tag):
        self._tags.append(tag)

    def remove_tag(self, tag):
        self._tags.remove(tag)

    def has_tag(self, tag):
        return tag in self._tags
    
    def has_child(self, child:SObject):
        return child in self._children
        
    T2 = TypeVar("T2", bound='SObject')
    def get_child_of_type(self, type: type[T2])->T2:
        for child in self._children:
            if isinstance(child, type):
                return child
        raise ValueError(f"Child of type {type} not found")
    
    T3=TypeVar("T3", bound='SObject')
    def get_children_of_type(self, type: type[T3])-> list[T3]:
        return [child for child in self._children if isinstance(child, type)]
    
    def get_children(self):
        return self._children.copy()
    
    def get_child_by_id(self, id:str)->SObject:
        for child in self._children:
            if child.get_id() == id:
                return child
        raise ValueError(f"Child {id} not found")
    
    def get_type_name(self):
        return self._server.get_object_type_name(self.__class__)
    
    T4 = TypeVar("T4", bound='SObject')
    def top_down_search(self, accept: Callable[['SObject'], bool]|None = None,stop: Callable[['SObject'], bool]|None = None, type:type[T4]=Self)-> list[T4]:
        result = []
        if type is Self:
            type = self.__class__ # type: ignore
        if isinstance(self, type):
            if accept is None or accept(self):
                result.append(self)
        if stop is None or not stop(self):
            for child in self._children:
                result += child.top_down_search(accept, stop, type)
        return result
    
    def __str__(self) -> str:
        return f"{self.get_type_name()}({self._id})"
    
    def __repr__(self) -> str:
        return self.__str__()