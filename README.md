# ObjectSync

ObjectSync is a communication framework designed for real-time applications, providing synchronization of state across a server and multiple clients. This README provides an overview of ObjectSync and its core concepts.

The ObjectSync client source code is at https://github.com/eri24816/ObjectSyncClient_ts

## Lifecycle of SObject changed from v0.4.0

![Image](https://i.imgur.com/CwYle7o.png)

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

Not available yet.

## Get Started

Here is a minimal script to start the objectsync server:
```python
import objectsync
import asyncio
server = objectsync.Server(port=8765)
asyncio.run(server.serve())
```

To create `SObject`s, you have to first define some subclasses of `SObject`.

For example:

```python
class TextObject(ElementObject):

    frontend_type = 'text'

    def pre_build(self, _):
        # Set up style and text attributes to get control of the DOM element's style and text
        self.style = self.add_attribute('style', objectsync.DictTopic, {})
        self.text = self.add_attribute('text', objectsync.StringTopic, '')
```

The class's `frontend_type` property is `'text'`, which means when a TextObject is created, an SObject of 'text' type will spawn in the frontend. The frontend `SObject` types have to be defined in the separate frontend code (in TypeScript), which is out of scope here. Let's just assume the attributes `style` and `text` is bind to a DOM element's style and text properties.

Spawn a TextObject with `server.create_object` and modify the attributes a bit:

```python
text = server.create_object(TextObject)
text.text.set('Hello ObjectSync!')
text.style.add('font-size','30px')
text.style.add('border','5px solid black')
text.style.add('background-color','yellow')
```

Then run the server.

```python
asyncio.run(server.serve())
```

The result will look like this:

![Image](https://i.imgur.com/hVFeewp.png)
