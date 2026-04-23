"""
client_cli.py
-------------
Cliente TCP de linha de comando para testar o servidor de leilões.
Roda duas threads:
  - Listener: recebe e exibe mensagens do servidor em tempo real.
  - Main: lê comandos do usuário e envia ao servidor.

Uso:
  python client_cli.py [host] [port]
"""

import socket
import threading
import json
import sys
import time
from protocol import ClientMessageType, build_client_message, decode_message

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5555


# ─────────────────────────────────────────────
#  Listener thread — exibe mensagens do servidor
# ─────────────────────────────────────────────

def listener(sock: socket.socket, stop_event: threading.Event):
    buffer = b""
    while not stop_event.is_set():
        try:
            chunk = sock.recv(4096)
        except OSError:
            break
        if not chunk:
            print("\n[!] Servidor desconectou.")
            stop_event.set()
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                msg = decode_message(line.decode("utf-8"))
                pretty = json.dumps(msg, ensure_ascii=False, indent=2)
                print(f"\n{'─'*50}\n📨 {msg['type']}\n{pretty}\n{'─'*50}")
            except Exception as e:
                print(f"[ERRO ao parsear mensagem]: {e} | raw: {line}")


# ─────────────────────────────────────────────
#  Menu interativo
# ─────────────────────────────────────────────

HELP = """
Comandos disponíveis:
  register <nome> [admin]   — Registrar no servidor (use 'admin' para ser administrador)
  add <nome> <preço> [desc] — Cadastrar item de leilão (somente admin)
  bid <item_id> <valor>     — Dar um lance
  close <item_id>           — Encerrar leilão (somente admin)
  list                      — Listar itens
  ping                      — Heartbeat
  quit                      — Sair
  help                      — Exibir este menu
"""


def send(sock: socket.socket, data: bytes):
    sock.sendall(data)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(f"[ERRO] Não foi possível conectar em {HOST}:{PORT}")
        sys.exit(1)

    print(f"✅ Conectado ao servidor {HOST}:{PORT}")
    print(HELP)

    stop_event = threading.Event()
    t = threading.Thread(target=listener, args=(sock, stop_event), daemon=True)
    t.start()

    try:
        while not stop_event.is_set():
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue

            parts = line.split(maxsplit=3)
            cmd = parts[0].lower()

            if cmd == "quit":
                break

            elif cmd == "help":
                print(HELP)

            elif cmd == "register":
                if len(parts) < 2:
                    print("Uso: register <nome> [admin]")
                    continue
                name = parts[1]
                is_admin = len(parts) > 2 and parts[2].lower() == "admin"
                send(sock, build_client_message(
                    ClientMessageType.REGISTER, name=name, is_admin=is_admin
                ))

            elif cmd == "add":
                if len(parts) < 3:
                    print("Uso: add <nome> <preço> [descrição]")
                    continue
                item_name = parts[1]
                try:
                    price = float(parts[2])
                except ValueError:
                    print("Preço inválido.")
                    continue
                desc = parts[3] if len(parts) > 3 else ""
                send(sock, build_client_message(
                    ClientMessageType.ADD_ITEM,
                    name=item_name,
                    description=desc,
                    starting_price=price,
                ))

            elif cmd == "bid":
                if len(parts) < 3:
                    print("Uso: bid <item_id> <valor>")
                    continue
                item_id = parts[1].upper()
                try:
                    amount = float(parts[2])
                except ValueError:
                    print("Valor inválido.")
                    continue
                send(sock, build_client_message(
                    ClientMessageType.PLACE_BID, item_id=item_id, amount=amount
                ))

            elif cmd == "close":
                if len(parts) < 2:
                    print("Uso: close <item_id>")
                    continue
                send(sock, build_client_message(
                    ClientMessageType.CLOSE_AUCTION, item_id=parts[1].upper()
                ))

            elif cmd == "list":
                send(sock, build_client_message(ClientMessageType.LIST_ITEMS))

            elif cmd == "ping":
                send(sock, build_client_message(ClientMessageType.PING))

            else:
                print(f"Comando desconhecido: '{cmd}'. Digite 'help' para ver os comandos.")

    finally:
        stop_event.set()
        sock.close()
        print("👋 Conexão encerrada.")


if __name__ == "__main__":
    main()