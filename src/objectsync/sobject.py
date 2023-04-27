from __future__ import annotations
from typing import List, Dict, Any, Optional, TypeVar, Union, TYPE_CHECKING
from chatroom.topic import SetTopic, Topic, IntTopic

if TYPE_CHECKING:
    from objectsync.server import Server

class SObject:
    def __init__(self, server:Server, id:int):
        self._server = server
        self._id = id
        self._children_ids = self._server.create_topic(f"_/{id}/children_ids", SetTopic, [])
        self._parent_id = self._server.create_topic(f"_/{id}/parent_id", IntTopic)
        self._parent_id.on_set2 += self._on_parent_changed

    '''
    Callbacks
    '''
    def _on_parent_changed(self, old_parent_id, new_parent_id):
        self._server.get_object(old_parent_id).remove_child(self)
        self._server.get_object(new_parent_id).add_child(self)

    '''
    Private methods
    '''
    
    T = TypeVar("T", bound=Topic)
    def _add_property(self, topic_name, topic_type: type[T], init_value) -> T:
        return self._server.create_topic(f"{self._id}/{topic_name}", topic_type, init_value)
    
    '''
    Public methods
    '''
    
    def get_id(self):
        return self._id
    
    def add_child(self, child:SObject):
        self._children_ids.append(child.get_id())

    def remove_child(self, child:SObject):
        self._children_ids.remove(child.get_id())
    
    def get_parent(self):
        if self._id == 0:
            raise NotImplementedError('Cannot call get_parent of root object')
        return self._server.get_object(self._parent_id.get())
    
    def on_destroy(self):
        self._server.remove_topic(self._children_ids.get_name())
        self._server.remove_topic(self._parent_id.get_name())