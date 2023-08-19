from __future__ import annotations
from typing import TYPE_CHECKING, Callable, List
from chatroom.change import Change
from chatroom.utils import Action
from chatroom.topic import ListTopic, DictTopic, SetTopic, Topic, StringTopic
from typing import TypeVar, Generic

from objectsync.utils import camel_to_snake

if TYPE_CHECKING:
    from objectsync.sobject import SObject

class WrappedTopic:
    @classmethod
    def get_type_name(cls):
        return camel_to_snake(cls.__name__[:-5])
    
    def __init__(self) -> None:
        self._topic : Topic

    def get_name(self):
        return self._topic.get_name()
    
    def is_stateful(self):
        return self._topic.is_stateful()
    
    def get_raw(self):
        return self._topic.get()
    
    def set(self, value):
        self._topic.set(value)

T = TypeVar('T', bound='SObject')
class ObjTopic(Generic[T],WrappedTopic):
    def __init__(self, topic: StringTopic,map: Callable[[str],T]):
        self._topic = topic
        self._map : Callable[[str],T]|None = map
        self.on_set = Action()
        self.on_set2 = Action()

        self._topic.on_set.add_raw(lambda auto, new_value: self.on_set.invoke(auto,self.map(new_value))\
            if self.on_set.num_callbacks > 0 else None) # Must have this check to avoid error when building (children not yet created)
        self._topic.on_set2.add_raw(lambda auto, old_value, new_value: self.on_set2.invoke(auto,self.map(old_value), self.map(new_value))\
            if self.on_set2.num_callbacks > 0 else None)

    def map(self,value:str):
        try:
            return self._map(value)
        except:
            return None

    def set(self, object:T):
        return self._topic.set(object.get_id())
    
    def get(self):
        return self.map(self._topic.get())

T = TypeVar('T', bound='SObject')
class ObjListTopic(Generic[T],WrappedTopic):
    def __init__(self, topic: ListTopic,map: Callable[[str],T]):
        self._topic:ListTopic = topic
        self._map : Callable[[str],T]|None = map
        self.on_set = Action()
        self.on_set2 = Action()
        self.on_insert = Action()
        self.on_pop = Action()

        self._topic.on_set.add_raw(lambda auto, new_value: self.on_set.invoke(auto,[self._map(x) for x in new_value])\
            if self.on_set.num_callbacks > 0 else None)
        self._topic.on_set2.add_raw(lambda auto, old_value, new_value: self.on_set2.invoke(auto,[self._map(x) for x in old_value], [self._map(x) for x in new_value])\
            if self.on_set2.num_callbacks > 0 else None)
        self._topic.on_insert.add_raw(lambda auto, value, index: self.on_insert.invoke(auto,self._map(value), index )\
            if self.on_insert.num_callbacks > 0 else None)
        self._topic.on_pop.add_raw(lambda auto, value, index: self.on_pop.invoke(auto,self._map(value), index )\
            if self.on_pop.num_callbacks > 0 else None)

    def set(self, objects:List[T]):
        return self._topic.set([x.get_id() for x in objects])

    def insert(self, object:T, position: int = -1):
        return self._topic.insert(object.get_id(), position)
    
    def remove(self, object:T):
        return self._topic.remove(object.get_id())
    
    def __iter__(self):
        old_gen = self._topic.__iter__()
        def new_gen():
            for x in old_gen:
                yield self._map(x)
        return new_gen()
        
    def __getitem__(self, key):
        return self._map(self._topic.__getitem__(key))
    
    def __setitem__(self, key, value):
        return self._topic.__setitem__(key, value.get_id())
    
    def __delitem__(self, key):
        return self._topic.__delitem__(key)
    
    def __len__(self):
        return self._topic.__len__()
    
    def get(self):
        return [self._map(x) for x in self._topic.get()]

T = TypeVar('T', bound='SObject')
class ObjSetTopic(Generic[T],WrappedTopic):
    def __init__(self, topic: SetTopic,map: Callable[[str],T]):
        self._topic:SetTopic = topic
        self._map : Callable[[str],T]|None = map
        self.on_set = Action()
        self.on_set2 = Action()
        self.on_append = Action()
        self.on_remove = Action()

        self._topic.on_set.add_raw(lambda auto, new_value: self.on_set.invoke(auto,[self._map(x) for x in new_value])\
            if self.on_set.num_callbacks > 0 else None)
        self._topic.on_set2.add_raw(lambda auto, old_value, new_value: self.on_set2.invoke(auto,[self._map(x) for x in old_value], [self._map(x) for x in new_value])\
            if self.on_set2.num_callbacks > 0 else None)
        self._topic.on_append.add_raw(lambda auto, value: self.on_append.invoke(auto,self._map(value))\
            if self.on_append.num_callbacks > 0 else None)
        self._topic.on_remove.add_raw(lambda auto, value: self.on_remove.invoke(auto,self._map(value))\
            if self.on_remove.num_callbacks > 0 else None)

    def set(self, objects:List[T]):
        return self._topic.set([x.get_id() for x in objects])

    def append(self, object:T):
        return self._topic.append(object.get_id())
    
    def remove(self, object:T):
        return self._topic.remove(object.get_id())
    
    def get(self):
        return {self._map(x) for x in self._topic.get()}

T = TypeVar('T', bound='SObject')    
class ObjDictTopic(Generic[T],WrappedTopic):
    def __init__(self, topic: DictTopic,map: Callable[[str],T]):
        self._topic:DictTopic = topic
        self._map : Callable[[str],T]|None = map

        self.on_set = Action()
        self.on_set2 = Action()
        self.on_add = Action()
        self.on_remove = Action()
        self.on_change_value = Action()
        
        self._topic.on_set.add_raw(lambda auto, new_value: self.on_set.invoke(auto,{k:self._map(v) for k,v in new_value.items()})\
            if self.on_set.num_callbacks > 0 else None)
        self._topic.on_set2.add_raw(lambda auto, old_value, new_value: self.on_set2.invoke(auto,{k:self._map(v) for k,v in old_value.items()}, {k:self._map(v) for k,v in new_value.items()})\
            if self.on_set2.num_callbacks > 0 else None)
        self._topic.on_add.add_raw(lambda auto, key, value: self.on_add.invoke(auto,key, self._map(value))\
            if self.on_add.num_callbacks > 0 else None)
        self._topic.on_remove.add_raw(lambda auto, key: self.on_remove.invoke(auto,key)\
            if self.on_remove.num_callbacks > 0 else None)
        self._topic.on_change_value.add_raw(lambda auto, key, new_value: self.on_change_value.invoke(auto,key, self._map(new_value))\
            if self.on_change_value.num_callbacks > 0 else None)

    def set(self, objects:dict):
        return self._topic.set({k:v.get_id() for k,v in objects.items()})

    def change_value(self, key, value:T):
        return self._topic.change_value(key, value.get_id())
    
    def add(self, key, value:T):
        return self._topic.add(key, value.get_id())
    
    def remove(self, key):
        return self._topic.remove(key)
    
    def pop(self, key):
        return self._map(self._topic.pop(key))

    def __getitem__(self, key):
        return self._map(self._topic.__getitem__(key))
    
    def __setitem__(self, key, value):
        return self._topic.__setitem__(key, value.get_id())
    
    def __delitem__(self, key):
        return self._topic.__delitem__(key)
    
    def notify_listeners(self,auto:bool, change: Change, old_value: dict, new_value: dict):
        old_value = {k:self._map(v) for k,v in old_value.items()}
        new_value = {k:self._map(v) for k,v in new_value.items()}
        return self._topic.notify_listeners(auto,change, old_value, new_value)
    
    def get(self):
        return {k:self._map(v) for k,v in self._topic.get().items()}
        

