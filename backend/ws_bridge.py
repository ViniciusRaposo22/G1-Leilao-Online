"""
ws_bridge.py
------------
Bridge WebSocket ↔ TCP para o frontend React.

O React não consegue abrir sockets TCP brutos no navegador.
Este bridge resolve isso:
  - Escuta conexões WebSocket (porta 6789)
  - Para cada cliente WS, abre uma conexão TCP com o AuctionServer
  - Encaminha mensagens em ambos os sentidos

Dependência: pip install websockets

Uso:
  python ws_bridge.py [ws_port] [tcp_host] [tcp_port]
"""

import asyncio
import sys
import logging
import json

try:
    import websockets
except ImportError:
    print("Instale: pip install websockets")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRIDGE] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("WsBridge")

WS_PORT  = int(sys.argv[1]) if len(sys.argv) > 1 else 6789
TCP_HOST = sys.argv[2]      if len(sys.argv) > 2 else "127.0.0.1"
TCP_PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 5555


async def handle_ws_client(websocket):
    """
    Cada cliente WebSocket ganha sua própria conexão TCP ao servidor de leilões.
    Dois tasks rodam em paralelo:
      - ws_to_tcp: lê do WS e escreve no TCP
      - tcp_to_ws: lê do TCP e escreve no WS
    """
    peer = websocket.remote_address
    log.info(f"WS conectado: {peer}")

    try:
        reader, writer = await asyncio.open_connection(TCP_HOST, TCP_PORT)
    except OSError as e:
        log.error(f"Falha ao conectar ao servidor TCP: {e}")
        await websocket.close(code=1011, reason="Servidor de leilões indisponível")
        return

    async def ws_to_tcp():
        """WS → TCP: repassa mensagens do navegador ao servidor."""
        async for message in websocket:
            try:
                # Valida que é JSON e adiciona '\n' como delimitador TCP
                json.loads(message)
                writer.write((message + "\n").encode("utf-8"))
                await writer.drain()
            except (json.JSONDecodeError, ConnectionResetError):
                break

    async def tcp_to_ws():
        """TCP → WS: repassa notificações do servidor ao navegador."""
        buffer = b""
        while True:
            try:
                chunk = await reader.read(4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip():
                    try:
                        await websocket.send(line.decode("utf-8"))
                    except Exception:
                        return

    try:
        await asyncio.gather(ws_to_tcp(), tcp_to_ws())
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        log.info(f"WS desconectado: {peer}")


async def main():
    log.info(f"Bridge WS:{WS_PORT} ↔ TCP {TCP_HOST}:{TCP_PORT} iniciado.")
    async with websockets.serve(
        handle_ws_client,
        "0.0.0.0",
        WS_PORT,
        ping_interval=20,
        ping_timeout=10,
    ):
        await asyncio.Future()  # roda indefinidamente


if __name__ == "__main__":
    asyncio.run(main())