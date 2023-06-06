from __future__ import annotations
from typing import TYPE_CHECKING, Callable, List
from chatroom.change import Change
from chatroom.utils import Action
from chatroom.topic import ListTopic, DictTopic, SetTopic, Topic, StringTopic
from typing import TypeVar, Generic

if TYPE_CHECKING:
    from objectsync.sobject import SObject

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

        self._topic.on_set += lambda new_value: self.on_set(self.map(new_value))\
            if len(self.on_set._callbacks) > 0 else None # Must have this check to avoid error when building (children not yet created)
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2(self.map(old_value), self.map(new_value))\
            if len(self.on_set2._callbacks) > 0 else None

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
class ObjListTopic(Generic[T]):
    @classmethod
    def get_type_name(cls):
        return 'list'
    def __init__(self, topic: ListTopic,map: Callable[[str],T]):
        self._topic = topic
        self._map : Callable[[str],T]|None = map
        self.on_set = Action()
        self.on_set2 = Action()
        self.on_insert = Action()
        self.on_pop = Action()

        self._topic.on_set += lambda new_value: self.on_set([self._map(x) for x in new_value])\
            if len(self.on_set._callbacks) > 0 else None
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2([self._map(x) for x in old_value], [self._map(x) for x in new_value])\
            if len(self.on_set2._callbacks) > 0 else None
        self._topic.on_insert += lambda value, index: self.on_insert(self._map(value), index )\
            if len(self.on_insert._callbacks) > 0 else None
        self._topic.on_pop += lambda value, index: self.on_pop(self._map(value), index )\
            if len(self.on_pop._callbacks) > 0 else None

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
class ObjSetTopic(Generic[T]):
    @classmethod
    def get_type_name(cls):
        return 'set'
    def __init__(self, topic: SetTopic,map: Callable[[str],T]):
        self._topic = topic
        self._map : Callable[[str],T]|None = map
        self.on_set = Action()
        self.on_set2 = Action()
        self.on_append = Action()
        self.on_remove = Action()

        self._topic.on_set += lambda new_value: self.on_set([self._map(x) for x in new_value])\
            if len(self.on_set._callbacks) > 0 else None
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2([self._map(x) for x in old_value], [self._map(x) for x in new_value])\
            if len(self.on_set2._callbacks) > 0 else None
        self._topic.on_append += lambda value: self.on_append(self._map(value))\
            if len(self.on_append._callbacks) > 0 else None
        self._topic.on_remove += lambda value: self.on_remove(self._map(value))\
            if len(self.on_remove._callbacks) > 0 else None

    def set(self, objects:List[T]):
        return self._topic.set([x.get_id() for x in objects])

    def append(self, object:T):
        return self._topic.append(object.get_id())
    
    def remove(self, object:T):
        return self._topic.remove(object.get_id())
    
    def get(self):
        return {self._map(x) for x in self._topic.get()}

T = TypeVar('T', bound='SObject')    
class ObjDictTopic(Generic[T]):
    @classmethod
    def get_type_name(cls):
        return 'dict'
    def __init__(self, topic: DictTopic,map: Callable[[str],T]):
        self._topic = topic
        self._map : Callable[[str],T]|None = map

        self.on_set = Action()
        self.on_set2 = Action()
        self.on_add = Action()
        self.on_remove = Action()
        self.on_change_value = Action()
        
        self._topic.on_set += lambda new_value: self.on_set({k:self._map(v) for k,v in new_value.items()})\
            if len(self.on_set._callbacks) > 0 else None
        self._topic.on_set2 += lambda old_value, new_value: self.on_set2({k:self._map(v) for k,v in old_value.items()}, {k:self._map(v) for k,v in new_value.items()})\
            if len(self.on_set2._callbacks) > 0 else None
        self._topic.on_add += lambda key, value: self.on_add(key, self._map(value))\
            if len(self.on_add._callbacks) > 0 else None
        self._topic.on_remove += lambda key, value: self.on_remove(key, self._map(value))\
            if len(self.on_remove._callbacks) > 0 else None
        self._topic.on_change_value += lambda key, new_value: self.on_change_value(key, self._map(new_value))\
            if len(self.on_change_value._callbacks) > 0 else None

    def set(self, objects:dict):
        return self._topic.set({k:v.get_id() for k,v in objects.items()})

    def change_value(self, key, value:T):
        return self._topic.change_value(key, value.get_id())
    
    def add(self, key, value:T):
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
        

