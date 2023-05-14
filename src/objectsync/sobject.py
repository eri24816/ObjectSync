from __future__ import annotations
from ast import Str
from typing import List, Dict, Any, Optional, TypeVar, Union, TYPE_CHECKING
from chatroom.topic import SetTopic, Topic, IntTopic, StringTopic

if TYPE_CHECKING:
    from objectsync.server import Server

class SObject:
    def __init__(self, server:Server, id:str, parent_id:str):
        self._server = server
        self._id = id
        self._parent_id = self._server.create_topic(f"_/{id}/parent_id", StringTopic, parent_id)
        self._parent_id.on_set2 += self._on_parent_changed
        self._attributes : Dict[str,Topic] = {}

    '''
    Callbacks
    '''
    def _on_parent_changed(self, old_parent_id, new_parent_id):
        self._server.get_object(old_parent_id).remove_child(self)
        self._server.get_object(new_parent_id).add_child(self)

    '''
    Private methods
    '''

    '''
    Public methods
    '''
    
    def get_id(self):
        return self._id
    
    def add_child(self, child:SObject):
        pass

    def remove_child(self, child:SObject):
        pass
    
    def get_parent(self):
        if self._id == 'root':
            raise NotImplementedError('Cannot call get_parent of root object')
        return self._server.get_object(self._parent_id.get())
    
    T = TypeVar("T", bound=Topic)
    def add_attribute(self, topic_name, topic_type: type[T], init_value) -> T:
        if topic_name in self._attributes:
            raise ValueError(f"Attribute '{topic_name}' already exists")
        new_attr = self._server.create_topic(f"{self._id}/{topic_name}", topic_type, init_value)
        self._attributes[topic_name] = new_attr
        return new_attr
    
    def on_destroy(self):
        self._server.remove_topic(self._parent_id.get_name())
        for attr in self._attributes.values():
            self._server.remove_topic(attr.get_name())