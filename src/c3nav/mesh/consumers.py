from channels.generic.websocket import AsyncWebsocketConsumer

from c3nav.mesh import messages


class MeshConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print('connected!')
        await self.accept()

    async def disconnect(self, close_code):
        print('disconnected!')
        pass

    async def send_msg(self, msg):
        print('Sending message:', msg)
        await self.send(bytes_data=msg.encode())

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data is None:
            return
        msg = messages.Message.decode(bytes_data)
        print('Received message:', msg)
        if isinstance(msg, messages.MeshSigninMessage):
            await self.send_msg(messages.MeshLayerAnnounceMessage(
                src='00:00:00:00:00:00',
                dst=msg.src,
                layer=messages.NO_LAYER
            ))
            await self.send_msg(messages.ConfigDumpMessage(
                src='00:00:00:00:00:00',
                dst=msg.src,
            ))
