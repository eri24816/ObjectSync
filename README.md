# ObjectSync

ObjectSync is a communication framework designed for real-time applications, providing synchronization of state across a server and multiple clients. This README provides an overview of ObjectSync and its core concepts.

## Introduction

ObjectSync enables real-time synchronization of state between a server and multiple clients. It achieves this by maintaining a hierarchy of `SObject`s, which represent synchronized objects. Each `SObject` contains several attributes that can be considered as variables or properties of the object.

When an `SObject` is created, it automatically appears on both the server and the clients, allowing seamless communication and synchronization. The attributes of the `SObject` can be accessed and modified by either the server code or the client code.

A common use case for ObjectSync is when representing a DOM element. An `SObject` can be used to represent a specific DOM element, and it can have an attribute called `style` that is bound to the element's style property. With ObjectSync, the server can modify the DOM element's style by simply modifying the `style` attribute in the server-side code, without the need to explicitly handle the communication between the server and the clients.

## Installation

### For Development

```bash
git clone git@github.com:eri24816/ObjectSync.git
cd ObjectSync
pip install -e .
```

### For Application

Not avaliable yet.

## Get Started

Here is a minimal script to start the objectsync server:
```python
import objectsync
import asyncio
server = objectsync.Server(port=8765)
asyncio.run(server.serve())
```

To define various type of `SObject`s that has various sets of attribute and functionalities, inherit the `SObject` class. For example:
```python
import asyncio
import objectsync

class ElementObject(objectsync.SObject):
    def __init__(self, server: objectsync.Server, id: str, parent_id: str):
        super().__init__(server, id, parent_id)
        self._style = self.add_attribute('style', objectsync.DictTopic, {})

class DivObject(ElementObject):
    def __init__(self, server: objectsync.Server, id: str, parent_id: str):
        super().__init__(server, id, parent_id)

class TextObject(ElementObject):
    def __init__(self, server: objectsync.Server, id: str, parent_id: str):
        super().__init__(server, id, parent_id)
        self._text = self.add_attribute('text', objectsync.StringTopic, '')

server = objectsync.Server(port=8765)
server.add_object_type('div',DivObject)
server.add_object_type('text',TextObject)
asyncio.run(server.serve())
```

Then add initial stuffs to be displayed

```python
...
div = server.create_object('div','root')
assert isinstance(div,DivObject)
text = server.create_object('text',div.get_id())
assert isinstance(text,TextObject)

# Modify the attributes to get fancy styling
text.text.set('Hello ObjectSync!')
text.style.add('font-size','20px')
text.style.add('border','5px solid black')
div.style.add('background-color','green')

asyncio.run(server.serve())
```