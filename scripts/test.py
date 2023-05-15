import asyncio
from typing import Any, Dict
import objectsync
import chatroom
chatroom.set_level(3)

class ElementObject(objectsync.SObject):
    frontend_type = 'div'
    def pre_build(self, attribute_values: Dict[str, Any] | None):
        self.style = self.add_attribute('style', objectsync.DictTopic, {})

class DivObject(ElementObject):
    frontend_type = 'div'
    pass

class TextObject(ElementObject):
    frontend_type = 'text'
    def pre_build(self, attribute_values: Dict[str, Any] | None):
        super().pre_build(attribute_values)
        self.text = self.add_attribute('text', objectsync.StringTopic, '')

class ListObject(ElementObject):
    frontend_type_name = 'div'
    def pre_build(self, attribute_values: Dict[str, Any] | None):
        super().pre_build(attribute_values)
        self.items = self.add_attribute('items', objectsync.SetTopic, [])

    def build(self):
        c1 = self.add_child(TextObject)
        c1.text.set('Hello')
        c2 = self.add_child(TextObject)
        c2.text.set('World')
        c3 = self.add_child(TextObject)
        c3.text.set('wyrwerywerywyr')


server = objectsync.Server(port=8765)
server.add_object_type(DivObject)
server.add_object_type(TextObject)
server.add_object_type(ListObject)

div = server.create_object(DivObject,'root')
text = server.create_object(TextObject,div.get_id())
with server.record():
    list_object = server.create_object(ListObject,'root')
    list_object.style.add('background-color','green')

# Modify the attributes to get fancy styling
text.text.set('Hello ObjectSync!')
text.style.add('font-size','20px')
text.style.add('border','5px solid black')
text.style.add('background-color','yellow')
div.style.add('background-color','blue')

asyncio.run(server.serve())
