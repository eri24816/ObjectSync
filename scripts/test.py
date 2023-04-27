import asyncio
import objectsync

server = objectsync.Server(8765)
asyncio.run(server.serve())
