#!/usr/bin/env python3
"""
Cliente de Leilão Eletrônico — v2
Suporte a múltiplos leilões: listar, escolher, dar lance em qualquer um.
"""

import socket
import threading
import json
import sys
import time
import os

HOST = "127.0.0.1"
PORT = 9000

# ─── ANSI ─────────────────────────────────────────────────────────────────────
R="\033[0m"; BOLD="\033[1m"; RED="\033[91m"; GREEN="\033[92m"
YELLOW="\033[93m"; CYAN="\033[96m"; WHITE="\033[97m"
MAGENTA="\033[95m"; GRAY="\033[90m"; BLUE="\033[94m"

def c(t, col): return f"{col}{t}{R}"

# ─── Cache local de leilões ───────────────────────────────────────────────────
auctions: dict = {}   # item_id → dict (snapshot)
my_username = ""
auctions_lock = threading.Lock()

def print_banner():
    print(c("""
╔══════════════════════════════════════════════╗
║     🔨 LEILÃO ELETRÔNICO v2 — CLIENTE       ║
╚══════════════════════════════════════════════╝""", CYAN))

def print_help():
    print(c("""
┌─ COMANDOS ────────────────────────────────────────┐
│  list              Listar todos os leilões         │
│  bid <id> <valor>  Dar lance em um leilão          │
│  new               Criar novo leilão               │
│  close <id>        Encerrar leilão (só seu)        │
│  info <id>         Detalhes de um leilão           │
│  help              Esta ajuda                      │
│  quit              Sair                            │
└───────────────────────────────────────────────────┘""", GRAY))

def print_auctions(items):
    if not items:
        print(c("\n  📭 Nenhum leilão ativo no momento.", YELLOW))
        return
    print(c(f"\n{'─'*62}", GRAY))
    print(c(f"  {'ID':>12}  {'ITEM':<22} {'LANCE ATUAL':>12}  {'QUEM':>10}  {'DONO'}", BOLD))
    print(c(f"{'─'*62}", GRAY))
    for it in items:
        me = it.get("owner") == my_username
        own_tag = c(" [SEU]", MAGENTA) if me else ""
        status  = "🔴" if it.get("status") == "closed" else "🟢"
        bid_str = f"R${float(it.get('current_bid',0)):>10.2f}"
        bidder  = (it.get("current_bidder") or "–")[:10]
        iid     = it.get("item_id","")[-10:]
        nm      = it.get("name","")[:22]
        print(f"  {status} {c(iid, CYAN):>12}  {nm:<22} {c(bid_str, GREEN):>12}  {bidder:>10}  {it.get('owner','')}{own_tag}")
    print(c(f"{'─'*62}\n", GRAY))

# ─── Render de mensagens recebidas ───────────────────────────────────────────
def render_message(msg: dict):
    t = msg.get("type")

    if t == "welcome":
        print(c(f"\n✅ {msg.get('message')}", GREEN))

    elif t == "item_list":
        with auctions_lock:
            for it in msg.get("items", []):
                auctions[it["item_id"]] = it
        print_auctions(msg.get("items", []))

    elif t == "auction_start":
        it = {k: msg[k] for k in
              ("item_id","name","description","starting_price","owner","status") if k in msg}
        it.setdefault("current_bid", 0)
        it.setdefault("current_bidder", "")
        it.setdefault("bid_count", 0)
        it.setdefault("status", "open")
        with auctions_lock:
            auctions[it["item_id"]] = it
        owner_tag = c(" [SEU]", MAGENTA) if msg.get("owner") == my_username else ""
        print(c(f"\n╔══ NOVO LEILÃO ══════════════════════════════", YELLOW))
        print(c(f"  {msg.get('name')}  {owner_tag}", WHITE))
        print(c(f"  {msg.get('description','')}", GRAY))
        print(c(f"  ID: {msg.get('item_id')}  |  Inicial: R${float(msg.get('starting_price',0)):.2f}", YELLOW))
        print(c(f"╚════════════════════════════════════════════", YELLOW))

    elif t == "new_bid":
        iid = msg.get("item_id")
        with auctions_lock:
            if iid in auctions:
                auctions[iid]["current_bid"]    = msg.get("amount")
                auctions[iid]["current_bidder"] = msg.get("bidder")
                auctions[iid]["bid_count"]       = msg.get("bid_count", 0)
        mine = msg.get("bidder") == my_username
        tag  = c(" ← você!", MAGENTA) if mine else ""
        print(c(f"\n  💰 [{msg.get('item_name')}] {msg.get('bidder')} → R${float(msg.get('amount',0)):.2f}  #{msg.get('bid_count')}{tag}", GREEN))

    elif t == "auction_end":
        iid = msg.get("item_id")
        with auctions_lock:
            if iid in auctions:
                auctions[iid]["status"] = "closed"
        winner = msg.get("winner")
        won_by_me = winner == my_username
        clr_fn = MAGENTA if won_by_me else BLUE
        print(c(f"""
╔══ 🏆 LEILÃO ENCERRADO ══════════════════════╗
  Item    : {msg.get('item_name')}
  Vencedor: {winner or 'nenhum'}{'  🎉 VOCÊ VENCEU!' if won_by_me else ''}
  Valor   : R${float(msg.get('winning_amount',0)):.2f}
  Lances  : {msg.get('bid_count',0)}
╚════════════════════════════════════════════╝""", clr_fn))

    elif t == "notice":
        print(c(f"\n  · {msg.get('message')}", GRAY))

    elif t == "ok":
        print(c(f"\n  ✔ {msg.get('message')}", GREEN))

    elif t == "error":
        print(c(f"\n  ✘ {msg.get('message')}", RED))

    print("", end="", flush=True)

# ─── Receiver thread ─────────────────────────────────────────────────────────
def receiver(sock):
    buffer = ""
    try:
        while True:
            chunk = sock.recv(4096).decode()
            if not chunk:
                print(c("\n[!] Conexão encerrada.", RED))
                os._exit(0)
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if line:
                    try:
                        render_message(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        print(c("\n[!] Conexão perdida.", RED))
        os._exit(1)

# ─── Helpers de envio ─────────────────────────────────────────────────────────
def send(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode())

def resolve_id(partial: str) -> str:
    """Aceita ID parcial (sufixo) e resolve para o item_id completo."""
    with auctions_lock:
        keys = list(auctions.keys())
    matches = [k for k in keys if k.endswith(partial) or k == partial]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(c(f"  Ambíguo: {matches} — use mais caracteres.", YELLOW))
        return ""
    # tenta correspondência parcial no nome
    matches = [k for k, v in auctions.items() if partial.lower() in v.get("name","").lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(c(f"  Múltiplos resultados pelo nome. Use o ID.", YELLOW))
        return ""
    print(c(f"  Leilão '{partial}' não encontrado. Use 'list' para ver os IDs.", RED))
    return ""

def prompt_new_item(sock):
    print(c("\n── Criar Novo Leilão ──────────────────────────", CYAN))
    name = input("  Nome do item    : ").strip()
    desc = input("  Descrição       : ").strip()
    try:
        price = float(input("  Lance inicial R$: ").strip().replace(",", "."))
    except ValueError:
        print(c("  Valor inválido.", RED)); return
    send(sock, {"cmd": "register_item", "name": name,
                "description": desc, "starting_price": price})

# ─── Main loop ────────────────────────────────────────────────────────────────
def main():
    global my_username
    print_banner()

    username = input(c("  Seu nome de usuário: ", CYAN)).strip()
    if not username:
        print(c("Nome inválido.", RED)); sys.exit(1)
    my_username = username

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(c(f"[ERRO] Servidor não disponível em {HOST}:{PORT}", RED)); sys.exit(1)

    send(sock, {"username": username})
    threading.Thread(target=receiver, args=(sock,), daemon=True).start()
    time.sleep(0.6)
    print_help()

    try:
        while True:
            try:
                line = input(c(f"\n[{username}] > ", BOLD)).strip()
            except EOFError:
                break
            if not line:
                continue

            parts = line.split()
            cmd   = parts[0].lower()

            if cmd in ("quit", "exit"):
                print(c("👋 Saindo…", GRAY)); break

            elif cmd == "list":
                send(sock, {"cmd": "list_items"})

            elif cmd == "bid":
                if len(parts) < 3:
                    print(c("  Uso: bid <id> <valor>    ex: bid 464432 850", RED)); continue
                iid = resolve_id(parts[1])
                if not iid: continue
                try:
                    amount = float(parts[2].replace(",", "."))
                except ValueError:
                    print(c("  Valor inválido.", RED)); continue
                send(sock, {"cmd": "bid", "item_id": iid, "amount": amount})

            elif cmd == "close":
                if len(parts) < 2:
                    print(c("  Uso: close <id>", RED)); continue
                iid = resolve_id(parts[1])
                if not iid: continue
                confirm = input(c(f"  Encerrar leilão '{iid}'? (s/n): ", YELLOW)).lower()
                if confirm == "s":
                    send(sock, {"cmd": "close_auction", "item_id": iid})

            elif cmd == "new":
                prompt_new_item(sock)

            elif cmd == "info":
                if len(parts) < 2:
                    print(c("  Uso: info <id>", RED)); continue
                iid = resolve_id(parts[1])
                if not iid: continue
                with auctions_lock:
                    it = auctions.get(iid)
                if not it:
                    print(c("  Leilão não encontrado localmente. Use 'list'.", RED)); continue
                print(c(f"""
┌─ DETALHES DO LEILÃO ─────────────────────────
│ ID      : {it.get('item_id')}
│ Item    : {it.get('name')}
│ Desc.   : {it.get('description','')}
│ Dono    : {it.get('owner')} {'← você' if it.get('owner')==my_username else ''}
│ Inicial : R${float(it.get('starting_price',0)):.2f}
│ Atual   : R${float(it.get('current_bid',0)):.2f}  ({it.get('current_bidder') or '–'})
│ Lances  : {it.get('bid_count',0)}
│ Status  : {it.get('status','?')}
└───────────────────────────────────────────────""", CYAN))

            elif cmd == "help":
                print_help()

            else:
                print(c(f"  Comando desconhecido: '{cmd}'. Digite 'help'.", RED))

    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        print(c("\nConexão encerrada.", GRAY))

if __name__ == "__main__":
    main()