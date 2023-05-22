from __future__ import annotations
from ast import Str
from dataclasses import dataclass
from mimetypes import init
from typing import List, Dict, Any, Optional, TypeVar, Union, TYPE_CHECKING
import typing
from chatroom.topic import SetTopic, Topic, IntTopic, StringTopic, DictTopic, ListTopic
from objectsync.topic import ObjDictTopic, ObjListTopic, ObjSetTopic, ObjTopic

from objectsync.history import History, HistoryItem
from objectsync.count import gen_id
from objectsync.topic import obj_ref

if TYPE_CHECKING:
    from objectsync.server import Server

@dataclass
class SObjectSerialized:
    id:str
    type:str
    attributes:Dict[str,Any]
    children:Dict[str,SObjectSerialized]


class SObject:
    frontend_type = 'Root'

    '''
    Initialization
    '''
    def __init__(self, server:Server, id:str, parent_id:str):
        self._server = server
        self._id = id
        self._parent_id = self._server.create_topic(f"parent_id/{id}", StringTopic, parent_id)
        self._tags = self._server.create_topic(f"tags/{id}", SetTopic)
        self._parent_id.on_set2 += self._on_parent_changed
        self._attributes : Dict[str,Topic] = {}
        self._children : List[SObject] = []
        self.history : History = History()


    def initialize(self, serialized:SObjectSerialized|None=None,prebuild_kwargs:Dict[str,Any]={}):
        if serialized is None:
            self.pre_build(None,**prebuild_kwargs)
        else:
            self.pre_build(serialized.attributes,**prebuild_kwargs)
        
        if serialized is None:
            self.build()
        else:
            self._deserialize(serialized)
        
        self.post_build()

    def pre_build(self, attribute_values:Dict[str,Any]|None):
        '''
        Create attributes for this object and set their initial values here.

        If the object is being created from scratch, the attribute_values argument is None.
        If the object is being restored, the attribute_values argument is the values of the attributes
        right before it was destroyed.

        You can choose either to explicitly restore the attributes' values by passing the values to their constructors here,
        or to safely leave them with default values and they'll still be automatically restored right after this method.
        '''

    def build(self):
        '''
        Create child objects here.
        Notice: This method will not be called when the object is being restored.
        '''

    def _deserialize(self, serialized:SObjectSerialized):
        for attr_name, attr_value in serialized.attributes.items():
            self._attributes[attr_name].set(attr_value)
        for child_id, child_serialized in serialized.children.items():
            self._server._create_object(child_serialized.type, self._id, child_id, child_serialized)
            self._children.append(self._server.get_object(child_id))

    def post_build(self):
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
        self._children.append(child)
    
    def _remove_child(self, child:SObject):
        print(f"Removing child {child.get_id()} from {self.get_id()}")
        self._children.remove(child)

    '''
    Public methods
    '''
    
    def get_id(self):
        return self._id
    
    def is_root(self):
        return self._id == 'root'

    T = TypeVar("T", bound='SObject')
    def add_child(self, type: type[T]) -> T:
        id = gen_id()
        self._server._create_object(type.__name__, self._id, id=id)
        new_child = self._server.get_object(id)
        assert isinstance(new_child, type)
        return new_child
    
    def get_parent(self):
        if self._id == 'root':
            raise NotImplementedError('Cannot call get_parent of root object')
        return self._server.get_object(self._parent_id.get())
    
    T1 = TypeVar("T1", bound=Topic|ObjTopic|ObjDictTopic|ObjListTopic|ObjSetTopic)
    def add_attribute(self, topic_name, topic_type: type[T1], init_value=None) -> T1: 
        origin_type = typing.get_origin(topic_type)
        if origin_type is None:
            origin_type = topic_type
        if topic_name in self._attributes:
            raise ValueError(f"Attribute '{topic_name}' already exists")
        if origin_type == ObjTopic:
            if init_value is not None:
                assert isinstance(init_value, SObject)
                init_value = init_value.get_id()
            new_attr = self.add_attribute(topic_name, StringTopic, init_value)
            new_attr = ObjTopic(new_attr, self._server.get_object)
            return new_attr # type: ignore
        if origin_type == ObjDictTopic:
            if init_value is not None:
                assert isinstance(init_value, Dict)
                init_value = {key: value.get_id() for key, value in init_value.items()}
            new_attr = self.add_attribute(topic_name, DictTopic, init_value)
            new_attr = ObjDictTopic(new_attr, self._server.get_object)
            return new_attr # type: ignore
        if origin_type == ObjListTopic:
            if init_value is not None:
                assert isinstance(init_value, list)
                init_value = [value.get_id() for value in init_value]
            new_attr = self.add_attribute(topic_name, ListTopic, init_value)
            new_attr = ObjListTopic(new_attr, self._server.get_object)
            return new_attr # type: ignore
        if origin_type == ObjSetTopic:
            if init_value is not None:
                assert isinstance(init_value, list)
                init_value = [value.get_id() for value in init_value]
            new_attr = self.add_attribute(topic_name, SetTopic, init_value)
            new_attr = ObjSetTopic(new_attr, self._server.get_object)
            return new_attr # type: ignore
        else:
            new_attr = self._server.create_topic(f"a/{self._id}/{topic_name}", topic_type, init_value) # type: ignore
        self._attributes[topic_name] = new_attr
        return new_attr
    
    def emit(self, event_name, **kwargs):
        self._server.emit(f"a/{self._id}/{event_name}", **kwargs)
    
    def on(self, event_name, callback):
        self._server.on(f"a/{self._id}/{event_name}", callback)
        
    
    def destroy(self)-> SObjectSerialized:
        self._server.remove_topic(self._parent_id.get_name())
        self._server.remove_topic(self._tags.get_name())

        attributes_serialized = {name: attr.get() for name, attr in self._attributes.items()}
        for attr in self._attributes.values():
            self._server.remove_topic(attr.get_name())

        children_serialized = {}
        for child in self._children.copy():
            child_info = self._server._destroy_object(child.get_id())
            children_serialized[child.get_id()] = child_info['serialized']

        return SObjectSerialized(
            id = self._id,
            type = self.__class__.__name__,
            attributes = attributes_serialized,
            children = children_serialized
        )
    
    def serialize(self) -> SObjectSerialized:
        attributes_serialized = {name: attr.get() for name, attr in self._attributes.items()}
        children_serialized = {child.get_id(): child.serialize() for child in self._children}
        return SObjectSerialized(
            id = self._id,
            type = self.__class__.__name__,
            attributes = attributes_serialized,
            children = children_serialized
        )
