import asyncio
import json

import pytest
import websockets

from webcam_ip.websocket_server import create_server

@pytest.fixture
async def server(event_loop):
    # Create server on a random port
    ws_server = create_server(host="127.0.0.1", port=0, websocket_path="/ws")
    server_task = event_loop.create_task(ws_server.start())

    # Give the server a moment to start
    await asyncio.sleep(0.1)

    # Extract the bound port
    sockets = ws_server.server.sockets
    assert sockets, "Server did not start"
    port = sockets[0].getsockname()[1]

    yield ws_server, port

    # Shutdown
    ws_server._shutdown_event.set()
    await ws_server.stop()
    server_task.cancel()


@pytest.mark.asyncio
async def test_ping(server):
    ws_server, port = server
    uri = f"ws://127.0.0.1:{port}/ws"

    async with websockets.connect(uri, subprotocols=["echo-protocol"]) as ws:
        # consume welcome notification
        await ws.recv()

        # send ping
        request = {"jsonrpc": "2.0", "method": "ping", "id": 1}
        await ws.send(json.dumps(request))

        response = json.loads(await ws.recv())
        assert response["jsonrpc"] == "2.0"
        assert response["result"] == "pong"
        assert response["id"] == 1


@pytest.mark.asyncio
async def test_echo_and_supported_methods(server):
    ws_server, port = server
    uri = f"ws://127.0.0.1:{port}/ws"

    async with websockets.connect(uri, subprotocols=["echo-protocol"]) as ws:
        await ws.recv()

        # test echo
        echo_req = {"jsonrpc": "2.0", "method": "echo", "params": {"message": "hello"}, "id": 2}
        await ws.send(json.dumps(echo_req))
        echo_res = json.loads(await ws.recv())
        assert echo_res["result"] == "hello"
        assert echo_res["id"] == 2

        # test get_supported_methods
        methods_req = {"jsonrpc": "2.0", "method": "get_supported_methods", "id": 3}
        await ws.send(json.dumps(methods_req))
        methods_res = json.loads(await ws.recv())
        assert "ping" in methods_res["result"]
        assert methods_res["id"] == 3


@pytest.mark.asyncio
async def test_get_server_info(server):
    ws_server, port = server
    uri = f"ws://127.0.0.1:{port}/ws"

    async with websockets.connect(uri, subprotocols=["echo-protocol"]) as ws:
        await ws.recv()

        req = {"jsonrpc": "2.0", "method": "get_server_info", "id": 4}
        await ws.send(json.dumps(req))
        res = json.loads(await ws.recv())

        assert "server" in res["result"]
        assert "system" in res["result"]
        assert "resources" in res["result"]
        assert res["id"] == 4


@pytest.mark.asyncio
async def test_camera_list_and_status(server):
    ws_server, port = server
    uri = f"ws://127.0.0.1:{port}/ws"

    async with websockets.connect(uri, subprotocols=["echo-protocol"]) as ws:
        await ws.recv()

        # get_camera_list
        list_req = {"jsonrpc": "2.0", "method": "get_camera_list", "id": 5}
        await ws.send(json.dumps(list_req))
        list_res = json.loads(await ws.recv())
        assert "cameras" in list_res["result"]
        assert "total" in list_res["result"]
        assert list_res["id"] == 5

        # get_camera_status (invalid device)
        status_req = {
            "jsonrpc": "2.0",
            "method": "get_camera_status",
            "params": {"device": "/dev/does_not_exist"},
            "id": 6
        }
        await ws.send(json.dumps(status_req))
        status_res = json.loads(await ws.recv())
        # since monitor not attached, fallback returns UNKNOWN status
        assert status_res["result"]["status"] in ("UNKNOWN",)
        assert status_res["id"] == 6


@pytest.mark.asyncio
async def test_invalid_method_and_malformed_json(server):
    ws_server, port = server
    uri = f"ws://127.0.0.1:{port}/ws"

    async with websockets.connect(uri, subprotocols=["echo-protocol"]) as ws:
        await ws.recv()

        # invalid method
        bad_req = {"jsonrpc": "2.0", "method": "no_such_method", "id": 7}
        await ws.send(json.dumps(bad_req))
        bad_res = json.loads(await ws.recv())
        assert bad_res["error"]["code"] == -32601  # Method not found

        # malformed JSON
        await ws.send('{"jsonrpc": "2.0", "method": ping, "id": 8}')
        mal_res = json.loads(await ws.recv())
        assert mal_res["error"]["code"] == -32700  # Parse error


@pytest.mark.asyncio
async def test_camera_status_notification(server):
    ws_server, port = server
    uri = f"ws://127.0.0.1:{port}/ws"

    recv_queue = asyncio.Queue()

    async def client():
        async with websockets.connect(uri, subprotocols=["echo-protocol"]) as ws:
            # consume welcome
            await ws.recv()
            # receive camera_status_update
            msg = await ws.recv()
            await recv_queue.put(msg)

    client_task = asyncio.create_task(client())
    await asyncio.sleep(0.1)  # allow client to connect

    # broadcast a test notification
    await ws_server.broadcast_camera_status({
        "device": "/dev/video0",
        "status": "CONNECTED",
        "resolution": "640x480",
        "fps": 30
    })

    msg = await asyncio.wait_for(recv_queue.get(), timeout=1.0)
    data = json.loads(msg)
    assert data["method"] == "camera_status_update"
    params = data["params"]
    assert params["device"] == "/dev/video0"
    assert params["status"] == "CONNECTED"

    client_task.cancel()
