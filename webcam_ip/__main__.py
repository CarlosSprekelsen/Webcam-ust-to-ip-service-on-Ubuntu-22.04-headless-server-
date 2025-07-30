# webcam_ip/__main__.py
from .config import Config
from .server import create_server

async def main():
    config = Config.load()
    server = create_server(
        host=config.server.host,
        port=config.server.port
    )
    await server.start()