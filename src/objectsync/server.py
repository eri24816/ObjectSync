from itertools import count
from typing import Dict, TypeVar
from chatroom import ChatroomServer
from chatroom.topic import Topic, IntTopic, SetTopic
from objectsync.sobject import SObject

class Server:
    def __init__(self, port: int, host:str='localhost') -> None:
        self._port = port
        self._host = host
        self._chatroom = ChatroomServer(port,host)
        self._id_counter = count(1)
        self._objects : Dict[int,SObject] = {}
        self._root_object = SObject(self,0)
        self._objects[0] = self._root_object
        self._object_ids = self.create_topic('object_ids',SetTopic,[0])
        self._object_ids.on_append += self._on_object_ids_append
        self._object_ids.on_remove += self._on_object_ids_remove

        self._chatroom.register_service('create_object',self.create_object,True)

    async def serve(self):
        '''
        Entry point for the server
        '''
        await self._chatroom.serve()

    '''
    Callbacks
    '''

    def _on_object_ids_append(self,id):
        print(f"Creating object with id {id}")
        obj = SObject(self,id)
        self._objects[id] = obj
        # Assign the new object to be root object's child initially.
        self._root_object.add_child(obj)

    def _on_object_ids_remove(self,id):
        obj = self._objects[id]
        obj.on_destroy()
        self._root_object.remove_child(obj)
        self._objects.pop(id)

    '''
    Basic methods
    '''

    def get_object(self, id:int) -> SObject:
        return self._objects[id]
    
    def create_object(self, parent_id:int) -> SObject:
        id = next(self._id_counter)
        self._object_ids.append(id)
        return self._objects[id]

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
