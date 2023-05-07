from itertools import count
from typing import Dict, TypeVar
import uuid
from chatroom import ChatroomServer
from chatroom.topic import Topic, IntTopic, SetTopic
from objectsync.sobject import SObject

class Server:
    def __init__(self, port: int, host:str='localhost') -> None:
        self._port = port
        self._host = host
        self._chatroom = ChatroomServer(port,host)
        self._objects : Dict[str,SObject] = {}
        root_id = uuid.uuid4().hex
        self._root_object = SObject(self,root_id)
        self._objects[root_id] = self._root_object
        self._object_ids = self.create_topic('object_ids',SetTopic,[root_id])

        # Link callbacks to chatroom events
        # so these mehtods can be called from both client and server
        self._chatroom.on('create_object', self._create_object)
        self._chatroom.on('destroy_object', self._destroy_object)

    async def serve(self):
        '''
        Entry point for the server
        '''
        await self._chatroom.serve()

    '''
    Callbacks
    '''

    def _create_object(self, id, parent_id):
        new_object = SObject(self,id)
        self._objects[id] = new_object
        self._object_ids.append(id)
        self._objects[parent_id].add_child(new_object)  
        return id
    
    def _destroy_object(self, id):
        obj = self._objects[id]
        obj.get_parent().remove_child(obj)
        obj.on_destroy()
        del self._objects[id]
        self._object_ids.remove(id)

    '''
    Basic methods
    '''

    def get_object(self, id:str) -> SObject:
        return self._objects[id]
    
    def create_object(self, parent_id:str, id:str|None = None) -> SObject:
        if id is None:
            id = uuid.uuid4().hex
        self._chatroom.emit('create_object', parent_id = parent_id)
        return self.get_object(id)
    
    def destroy_object(self, id:str):
        self._chatroom.emit('destroy_object', id = id)

    '''
    Encapsulate the chatroom server
    '''

    T = TypeVar('T', bound=Topic)
    def create_topic(self, topic_name, topic_type: type[T],init_value=None) -> T:
        topic = self._chatroom.add_topic(topic_name,topic_type)
        if init_value is not None:
            topic.set(init_value)
        return topic

    T = TypeVar('T', bound=Topic)
    def get_topic(self, topic_name, type: type[T]) -> T:
        return self._chatroom.get_topic(topic_name,type)
    
    def remove_topic(self, topic_name):
        self._chatroom.remove_topic(topic_name)
