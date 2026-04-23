"""
server.py
---------
Servidor TCP do sistema de leilões eletrônicos.

Arquitetura:
  - Thread principal: aceita conexões (socket.accept loop)
  - Thread por cliente: lê mensagens e despacha handlers
  - AuctionManager: estado compartilhado protegido por RLock
  - Broadcast: itera sobre clientes conectados com lock separado

Protocolo: JSON sobre TCP, mensagens delimitadas por '\n'.
"""

import socket
import threading
import logging
import sys
from typing import Dict, Set

from protocol import (
    ClientMessageType,
    ServerMessageType,
    build_server_message,
    decode_message,
)
from auction_manager import AuctionManager

# ─────────────────────────────────────────────
#  Configuração de logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("AuctionServer")


# ─────────────────────────────────────────────
#  Registro de clientes conectados
# ─────────────────────────────────────────────

class ClientRegistry:
    """
    Mantém o mapa de clientes conectados.
    Cada entrada: addr → {"socket": ..., "name": ..., "is_admin": ...}
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._clients: Dict[str, dict] = {}

    def register(self, addr: str, sock: socket.socket, name: str, is_admin: bool):
        with self._lock:
            self._clients[addr] = {
                "socket": sock,
                "name": name,
                "is_admin": is_admin,
            }

    def unregister(self, addr: str):
        with self._lock:
            self._clients.pop(addr, None)

    def get(self, addr: str) -> dict | None:
        with self._lock:
            return self._clients.get(addr)

    def broadcast(self, data: bytes, exclude: str = None):
        """Envia `data` para todos os clientes registrados (exceto `exclude`)."""
        with self._lock:
            dead = []
            for addr, info in self._clients.items():
                if addr == exclude:
                    continue
                try:
                    info["socket"].sendall(data)
                except OSError:
                    dead.append(addr)
            for addr in dead:
                del self._clients[addr]

    def send_to(self, addr: str, data: bytes):
        with self._lock:
            info = self._clients.get(addr)
            if info:
                try:
                    info["socket"].sendall(data)
                except OSError:
                    pass

    def count(self) -> int:
        with self._lock:
            return len(self._clients)


# ─────────────────────────────────────────────
#  Handler de cliente (roda em thread própria)
# ─────────────────────────────────────────────

class ClientHandler(threading.Thread):
    """
    Thread dedicada a um cliente TCP.
    Lê mensagens linha a linha (delimitadas por '\n') e despacha handlers.
    """

    def __init__(
        self,
        conn: socket.socket,
        addr: tuple,
        registry: ClientRegistry,
        manager: AuctionManager,
    ):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr_tuple = addr
        self.addr = f"{addr[0]}:{addr[1]}"
        self.registry = registry
        self.manager = manager
        self.name_tag = f"[{self.addr}]"

    # ── Leitura de stream ────────────────────

    def _read_lines(self):
        """Gerador que lê linhas completas do socket TCP."""
        buffer = b""
        while True:
            try:
                chunk = self.conn.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if line.strip():
                    yield line.decode("utf-8", errors="replace")

    # ── Loop principal ───────────────────────

    def run(self):
        log.info(f"{self.name_tag} Conexão estabelecida.")
        registered = False

        try:
            for raw in self._read_lines():
                try:
                    msg = decode_message(raw)
                except Exception:
                    self._send(build_server_message(
                        ServerMessageType.ERROR, message="Mensagem inválida (JSON malformado)."
                    ))
                    continue

                msg_type = msg.get("type")
                payload = msg.get("payload", {})

                # Primeiro passo obrigatório: REGISTER
                if not registered:
                    if msg_type == ClientMessageType.REGISTER:
                        registered = self._handle_register(payload)
                    else:
                        self._send(build_server_message(
                            ServerMessageType.ERROR,
                            message="Envie REGISTER antes de qualquer outra mensagem.",
                        ))
                    continue

                # Despacho de mensagens
                if msg_type == ClientMessageType.ADD_ITEM:
                    self._handle_add_item(payload)
                elif msg_type == ClientMessageType.PLACE_BID:
                    self._handle_place_bid(payload)
                elif msg_type == ClientMessageType.CLOSE_AUCTION:
                    self._handle_close_auction(payload)
                elif msg_type == ClientMessageType.LIST_ITEMS:
                    self._handle_list_items()
                elif msg_type == ClientMessageType.PING:
                    self._send(build_server_message(ServerMessageType.PONG))
                else:
                    self._send(build_server_message(
                        ServerMessageType.ERROR, message=f"Tipo de mensagem desconhecido: {msg_type}"
                    ))

        finally:
            self.registry.unregister(self.addr)
            try:
                self.conn.close()
            except OSError:
                pass
            log.info(f"{self.name_tag} Desconectado. Clientes ativos: {self.registry.count()}")

    # ── Handlers ─────────────────────────────

    def _handle_register(self, payload: dict) -> bool:
        name = payload.get("name", "").strip()
        is_admin = bool(payload.get("is_admin", False))

        if not name:
            self._send(build_server_message(
                ServerMessageType.ERROR, message="Campo 'name' é obrigatório no REGISTER."
            ))
            return False

        self.registry.register(self.addr, self.conn, name, is_admin)
        self.name_tag = f"[{name}@{self.addr}]"
        log.info(f"{self.name_tag} Registrado. Admin={is_admin}. Clientes ativos: {self.registry.count()}")

        self._send(build_server_message(
            ServerMessageType.WELCOME,
            name=name,
            is_admin=is_admin,
            message=f"Bem-vindo ao leilão, {name}!",
        ))
        return True

    def _handle_add_item(self, payload: dict):
        client = self.registry.get(self.addr)
        if not client or not client["is_admin"]:
            self._send(build_server_message(
                ServerMessageType.ERROR, message="Apenas administradores podem cadastrar itens."
            ))
            return

        name = payload.get("name", "").strip()
        description = payload.get("description", "").strip()
        starting_price = payload.get("starting_price", 0)

        if not name or starting_price <= 0:
            self._send(build_server_message(
                ServerMessageType.ERROR,
                message="Informe 'name' e 'starting_price' (> 0) para cadastrar item.",
            ))
            return

        item = self.manager.add_item(name, description, float(starting_price))
        log.info(f"{self.name_tag} Cadastrou item: {item.name} (ID={item.item_id})")

        broadcast_msg = build_server_message(
            ServerMessageType.ITEM_ADDED,
            item=item.to_dict(),
            message=f"Novo item disponível para leilão: {item.name}",
        )
        self.registry.broadcast(broadcast_msg)

    def _handle_place_bid(self, payload: dict):
        client = self.registry.get(self.addr)
        if not client:
            return

        item_id = payload.get("item_id", "").strip().upper()
        amount = payload.get("amount", 0)
        bidder = client["name"]

        if not item_id or not isinstance(amount, (int, float)) or amount <= 0:
            self._send(build_server_message(
                ServerMessageType.ERROR,
                message="Informe 'item_id' e 'amount' (> 0) para dar um lance.",
            ))
            return

        success, reason, bid = self.manager.place_bid(item_id, bidder, float(amount))

        if not success:
            self._send(build_server_message(
                ServerMessageType.BID_REJECTED, message=reason
            ))
            return

        log.info(f"{self.name_tag} Lance aceito: R$ {amount:.2f} no item {item_id}")

        # Notifica TODOS (inclusive o remetente)
        broadcast_msg = build_server_message(
            ServerMessageType.BID_ACCEPTED,
            bid=bid.to_dict(),
            message=f"{bidder} deu um lance de R$ {amount:.2f} no item {item_id}",
        )
        self.registry.broadcast(broadcast_msg)

    def _handle_close_auction(self, payload: dict):
        client = self.registry.get(self.addr)
        if not client or not client["is_admin"]:
            self._send(build_server_message(
                ServerMessageType.ERROR, message="Apenas administradores podem encerrar leilões."
            ))
            return

        item_id = payload.get("item_id", "").strip().upper()
        if not item_id:
            self._send(build_server_message(
                ServerMessageType.ERROR, message="Informe 'item_id' para encerrar o leilão."
            ))
            return

        success, reason, item = self.manager.close_auction(item_id)

        if not success:
            self._send(build_server_message(ServerMessageType.ERROR, message=reason))
            return

        log.info(
            f"{self.name_tag} Encerrou leilão do item {item_id}. "
            f"Vencedor: {item.current_winner} — R$ {item.current_price:.2f}"
        )

        winner = item.current_winner or "Nenhum lance recebido"
        broadcast_msg = build_server_message(
            ServerMessageType.AUCTION_CLOSED,
            item=item.to_dict(),
            winner=winner,
            final_price=item.current_price,
            message=(
                f"Leilão encerrado! Vencedor: {winner} "
                f"com R$ {item.current_price:.2f}"
            ),
        )
        self.registry.broadcast(broadcast_msg)

    def _handle_list_items(self):
        items = self.manager.list_all_items()
        self._send(build_server_message(
            ServerMessageType.ITEMS_LIST,
            items=[i.to_dict() for i in items],
        ))

    # ── Utilitário ───────────────────────────

    def _send(self, data: bytes):
        try:
            self.conn.sendall(data)
        except OSError as e:
            log.warning(f"{self.name_tag} Falha ao enviar mensagem: {e}")


# ─────────────────────────────────────────────
#  Servidor principal
# ─────────────────────────────────────────────

class AuctionServer:
    """
    Servidor TCP que aceita conexões e spawna uma ClientHandler thread
    para cada cliente.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5555):
        self.host = host
        self.port = port
        self.registry = ClientRegistry()
        self.manager = AuctionManager()
        self._server_sock: socket.socket | None = None

    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(64)

        log.info(f"Servidor de leilões iniciado em {self.host}:{self.port}")
        log.info("Aguardando conexões…")

        try:
            while True:
                try:
                    conn, addr = self._server_sock.accept()
                except OSError:
                    break

                handler = ClientHandler(conn, addr, self.registry, self.manager)
                handler.start()

        except KeyboardInterrupt:
            log.info("Servidor encerrado pelo operador.")
        finally:
            if self._server_sock:
                self._server_sock.close()


# ─────────────────────────────────────────────
#  Entrypoint
# ─────────────────────────────────────────────

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5555

    server = AuctionServer(host=host, port=port)
    server.start()