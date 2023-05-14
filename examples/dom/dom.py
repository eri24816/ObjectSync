import asyncio
import objectsync

class ElementObject(objectsync.SObject):
    def __init__(self, server: objectsync.Server, id: str, parent_id: str):
        super().__init__(server, id, parent_id)
        self.style = self.add_attribute('style', objectsync.DictTopic, {})

class DivObject(ElementObject):
    pass

class TextObject(ElementObject):
    def __init__(self, server: objectsync.Server, id: str, parent_id: str):
        super().__init__(server, id, parent_id)
        self.text = self.add_attribute('text', objectsync.StringTopic, '')

server = objectsync.Server(port=8765)
server.add_object_type('div',DivObject)
server.add_object_type('text',TextObject)

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
