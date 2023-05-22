from __future__ import annotations
from typing import TYPE_CHECKING, Callable, List
from chatroom.change import Change
from chatroom.utils import Action
from chatroom.topic import ListTopic, DictTopic, SetTopic, Topic, StringTopic
from typing import TypeVar, Generic

if TYPE_CHECKING:
    from objectsync.sobject import SObject
print(TYPE_CHECKING)

def obj_ref(topic:Topic,server):
    match topic:
        case ListTopic():
            return ObjListTopic(topic,server.get_object)
        case SetTopic():
            return ObjSetTopic(topic,server.get_object)
        case DictTopic():
            return ObjDictTopic(topic,server.get_object)

T = TypeVar('T', bound='SObject')
class ObjTopic(Generic[T]):
    @classmethod
    def get_type_name(cls):
        return 'string'
    def __init__(self, topic: StringTopic,map: Callable[[str],T]):
        self._topic = topic
        self._map : Callable[[str],T]|None = map
        self.on_set = Action()
        self.on_set2 = Action()

        self._topic.on_set += lambda new_value: self.on_set(self.map(new_value))
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2(self.map(old_value), self.map(new_value))

    def map(self,value:str):
        try:
            return self._map(value)
        except:
            return None

    def set(self, object:T):
        return self._topic.set(object.get_id())
    
    def get(self):
        return self.map(self._topic.get())

class ObjListTopic:
    @classmethod
    def get_type_name(cls):
        return 'list'
    def __init__(self, topic: ListTopic,map: Callable[[str],SObject]):
        self._topic = topic
        self._map : Callable[[str],SObject]|None = map
        self.on_set = Action()
        self.on_set2 = Action()
        self.on_insert = Action()
        self.on_pop = Action()

        self._topic.on_set += lambda new_value: self.on_set([self._map(x) for x in new_value])
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2([self._map(x) for x in old_value], [self._map(x) for x in new_value])
        self._topic.on_insert += lambda value, index: self.on_insert(self._map(value), index )
        self._topic.on_pop += lambda value, index: self.on_pop(self._map(value), index )

    def set(self, objects:List[SObject]):
        return self._topic.set([x.get_id() for x in objects])

    def insert(self, object:SObject, position: int = -1):
        return self._topic.insert(object.get_id(), position)
    
    def remove(self, object:SObject):
        return self._topic.remove(object.get_id())
        
    def __getitem__(self, key):
        return self._map(self._topic.__getitem__(key))
    
    def __setitem__(self, key, value):
        return self._topic.__setitem__(key, value.get_id())
    
    def __delitem__(self, key):
        return self._topic.__delitem__(key)
    
    def get(self):
        return [self._map(x) for x in self._topic.get()]
    
class ObjSetTopic:
    @classmethod
    def get_type_name(cls):
        return 'set'
    def __init__(self, topic: SetTopic,map: Callable[[str],SObject]):
        self._topic = topic
        self._map : Callable[[str],SObject]|None = map
        self.on_set = Action()
        self.on_set2 = Action()
        self.on_append = Action()
        self.on_remove = Action()

        self._topic.on_set += lambda new_value: self.on_set([self._map(x) for x in new_value])
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2([self._map(x) for x in old_value], [self._map(x) for x in new_value])
        self._topic.on_append += lambda value: self.on_append(self._map(value))
        self._topic.on_remove += lambda value: self.on_remove(self._map(value))

    def set(self, objects:List[SObject]):
        return self._topic.set([x.get_id() for x in objects])

    def append(self, object:SObject):
        return self._topic.append(object.get_id())
    
    def remove(self, object:SObject):
        return self._topic.remove(object.get_id())
    
    def get(self):
        return {self._map(x) for x in self._topic.get()}
    
class ObjDictTopic:
    @classmethod
    def get_type_name(cls):
        return 'dict'
    def __init__(self, topic: DictTopic,map: Callable[[str],SObject]):
        self._topic = topic
        self._map : Callable[[str],SObject]|None = map

        self.on_set = Action()
        self.on_set2 = Action()
        self.on_add = Action()
        self.on_remove = Action()
        self.on_change_value = Action()
        
        self._topic.on_set += lambda new_value: self.on_set({k:self._map(v) for k,v in new_value.items()})
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2({k:self._map(v) for k,v in old_value.items()}, {k:self._map(v) for k,v in new_value.items()})
        self._topic.on_add += lambda key, value: self.on_add(key, self._map(value))
        self._topic.on_remove += lambda key, value: self.on_remove(key, self._map(value))
        self._topic.on_change_value += lambda key, new_value: self.on_change_value(key, self._map(new_value))

    def set(self, objects:dict):
        return self._topic.set({k:v.get_id() for k,v in objects.items()})

    def change_value(self, key, value:SObject):
        return self._topic.change_value(key, value.get_id())
    
    def add(self, key, value:SObject):
        return self._topic.add(key, value.get_id())
    
    def remove(self, key):
        return self._topic.remove(key)

    def __getitem__(self, key):
        return self._map(self._topic.__getitem__(key))
    
    def __setitem__(self, key, value):
        return self._topic.__setitem__(key, value.get_id())
    
    def __delitem__(self, key):
        return self._topic.__delitem__(key)
    
    def notify_listeners(self, change: Change, old_value: dict, new_value: dict):
        old_value = {k:self._map(v) for k,v in old_value.items()}
        new_value = {k:self._map(v) for k,v in new_value.items()}
        return self._topic.notify_listeners(change, old_value, new_value)
    
    def get(self):
        return {k:self._map(v) for k,v in self._topic.get().items()}
        

