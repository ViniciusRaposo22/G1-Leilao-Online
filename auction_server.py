#!/usr/bin/env python3
"""
Servidor de Leilão Eletrônico — v2
Múltiplos leilões simultâneos, controle de dono, threads por cliente.
"""

import socket
import threading
import json
import time
import datetime
from dataclasses import dataclass, field, asdict

HOST     = "0.0.0.0"
PORT     = 9000
LOG_FILE = "auction_log.json"

# ─── Estruturas ───────────────────────────────────────────────────────────────
@dataclass
class Bid:
    bidder: str
    amount: float
    timestamp: str

@dataclass
class AuctionItem:
    item_id: str
    name: str
    description: str
    starting_price: float
    owner: str
    current_bid: float = 0.0
    current_bidder: str = ""
    bids: list = field(default_factory=list)
    status: str = "open"
    started_at: str = ""
    ended_at: str = ""
    winner: str = ""
    winning_amount: float = 0.0

# ─── Estado Global ────────────────────────────────────────────────────────────
state_lock      = threading.Lock()
clients: dict   = {}          # username → socket
auction_items: dict = {}      # item_id  → AuctionItem
auction_history = []

# ─── Helpers ──────────────────────────────────────────────────────────────────
def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_msg(sock, msg):
    try:
        sock.sendall((json.dumps(msg) + "\n").encode())
        return True
    except Exception:
        return False

def broadcast(msg, exclude=""):
    dead = []
    with state_lock:
        targets = dict(clients)
    for u, s in targets.items():
        if u == exclude:
            continue
        if not send_msg(s, msg):
            dead.append(u)
    for u in dead:
        remove_client(u)

def remove_client(username):
    with state_lock:
        sock = clients.pop(username, None)
    if sock:
        try: sock.close()
        except Exception: pass
    print(f"[INFO] Desconectado: {username}")
    broadcast({"type": "notice", "message": f"🔌 {username} saiu."})

def save_history():
    try:
        data = {"generated_at": now_str(),
                "auctions": [asdict(i) for i in auction_history]}
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Histórico salvo em {LOG_FILE}")
    except Exception as e:
        print(f"[ERRO] {e}")

def item_summary(item):
    return {
        "item_id":        item.item_id,
        "name":           item.name,
        "description":    item.description,
        "starting_price": item.starting_price,
        "owner":          item.owner,
        "current_bid":    item.current_bid,
        "current_bidder": item.current_bidder,
        "bid_count":      len(item.bids),
        "status":         item.status,
        "started_at":     item.started_at,
    }

# ─── Handlers ─────────────────────────────────────────────────────────────────
def handle_register_item(username, payload):
    item_id = f"item_{int(time.time() * 1000) % 10**9}"
    with state_lock:
        while item_id in auction_items:
            item_id += "_"
        item = AuctionItem(
            item_id        = item_id,
            name           = payload.get("name", "Sem nome"),
            description    = payload.get("description", ""),
            starting_price = float(payload.get("starting_price", 0)),
            owner          = username,
            started_at     = now_str(),
        )
        auction_items[item_id] = item

    print(f"[LEILÃO] {username} criou «{item.name}» R${item.starting_price:.2f} → {item_id}")
    broadcast({
        "type":           "auction_start",
        "item_id":        item_id,
        "name":           item.name,
        "description":    item.description,
        "starting_price": item.starting_price,
        "owner":          username,
        "message":        f"🔔 {username} abriu leilão: «{item.name}» — inicial R${item.starting_price:.2f}",
    })
    return {"type": "ok", "message": f"Leilão «{item.name}» aberto! ID: {item_id}"}


def handle_bid(username, payload):
    item_id = payload.get("item_id", "")
    with state_lock:
        item = auction_items.get(item_id)
        if not item:
            return {"type": "error", "message": "Leilão não encontrado."}
        if item.status != "open":
            return {"type": "error", "message": "Este leilão já foi encerrado."}
        if item.owner == username:
            return {"type": "error", "message": "Você não pode dar lance no seu próprio leilão."}

        amount  = float(payload.get("amount", 0))
        min_bid = item.starting_price if item.current_bid == 0 else item.current_bid
        if amount <= min_bid:
            return {"type": "error", "message": f"Lance deve ser maior que R${min_bid:.2f}."}

        item.bids.append(asdict(Bid(username, amount, now_str())))
        item.current_bid    = amount
        item.current_bidder = username
        snap = item_summary(item)

    print(f"[LANCE] {username} → R${amount:.2f} em «{item.name}»")
    broadcast({
        "type":      "new_bid",
        "item_id":   item_id,
        "item_name": item.name,
        "bidder":    username,
        "amount":    amount,
        "bid_count": snap["bid_count"],
        "message":   f"💰 [{item.name}] {username} → R${amount:.2f}",
    })
    return {"type": "ok", "message": f"Lance de R${amount:.2f} registrado em «{item.name}»!"}


def handle_close_auction(username, payload):
    item_id = payload.get("item_id", "")
    with state_lock:
        item = auction_items.get(item_id)
        if not item:
            return {"type": "error", "message": "Leilão não encontrado."}
        if item.status != "open":
            return {"type": "error", "message": "Leilão já encerrado."}
        if item.owner != username:
            return {"type": "error", "message": "Apenas o dono pode encerrar este leilão."}

        item.status         = "closed"
        item.ended_at       = now_str()
        item.winner         = item.current_bidder
        item.winning_amount = item.current_bid
        auction_history.append(item)

    print(f"[FIM] «{item.name}» → {item.winner or 'sem lances'} R${item.winning_amount:.2f}")
    save_history()

    msg = (f"🏆 Leilão encerrado: «{item.name}»\n"
           f"Vencedor: {item.winner} — R${item.winning_amount:.2f} | {len(item.bids)} lances"
           if item.winner else
           f"🔕 Leilão «{item.name}» encerrado sem lances.")

    broadcast({
        "type":           "auction_end",
        "item_id":        item.item_id,
        "item_name":      item.name,
        "owner":          item.owner,
        "winner":         item.winner,
        "winning_amount": item.winning_amount,
        "bid_count":      len(item.bids),
        "message":        msg,
    })
    return {"type": "ok", "message": f"Leilão «{item.name}» encerrado com sucesso."}


def handle_list_items(username):
    with state_lock:
        items = [item_summary(i) for i in auction_items.values()]
    return {"type": "item_list", "items": items}


# ─── Thread por cliente ────────────────────────────────────────────────────────
def handle_client(conn, addr):
    username = None
    buffer   = ""
    try:
        conn.settimeout(30)
        raw = conn.recv(2048).decode()
        conn.settimeout(None)
        pkt      = json.loads(raw.strip())
        username = pkt.get("username", f"user_{addr[1]}")

        with state_lock:
            if username in clients:
                send_msg(conn, {"type": "error", "message": "Nome já em uso."})
                conn.close()
                return
            clients[username] = conn

        print(f"[CONEXÃO] {username} @ {addr}")
        send_msg(conn, {"type": "welcome", "username": username,
                        "message": f"Bem-vindo ao Leilão Eletrônico, {username}!"})
        # Sincroniza todos os leilões abertos
        with state_lock:
            open_items = [item_summary(i) for i in auction_items.values() if i.status == "open"]
        send_msg(conn, {"type": "item_list", "items": open_items})
        broadcast({"type": "notice", "message": f"👤 {username} entrou."}, exclude=username)

        while True:
            chunk = conn.recv(4096).decode()
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    send_msg(conn, {"type": "error", "message": "JSON inválido."})
                    continue

                cmd = msg.get("cmd")
                if   cmd == "register_item":  resp = handle_register_item(username, msg)
                elif cmd == "bid":            resp = handle_bid(username, msg)
                elif cmd == "close_auction":  resp = handle_close_auction(username, msg)
                elif cmd == "list_items":     resp = handle_list_items(username)
                elif cmd == "ping":           resp = {"type": "pong"}
                else:                         resp = {"type": "error", "message": "Comando desconhecido."}
                send_msg(conn, resp)

    except (ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        print(f"[ERRO] {username or addr}: {e}")
    finally:
        if username:
            remove_client(username)
        else:
            try: conn.close()
            except Exception: pass

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("   🔨 SERVIDOR DE LEILÃO ELETRÔNICO v2")
    print(f"   Host: {HOST}  |  Porta: {PORT}")
    print("   Múltiplos leilões simultâneos")
    print("=" * 55)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(100)
    print(f"[OK] Escutando em {HOST}:{PORT}\n")
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[INFO] Servidor encerrado.")
    finally:
        srv.close()

if __name__ == "__main__":
    main()