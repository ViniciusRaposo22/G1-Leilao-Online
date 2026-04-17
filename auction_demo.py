#!/usr/bin/env python3
"""
Demo v2 — múltiplos leilões simultâneos, validação de dono.
"""
import subprocess, socket, json, time, threading, sys

HOST, PORT = "127.0.0.1", 9000

def send(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode())

def recv(sock, timeout=1.5):
    msgs, buf = [], ""
    sock.settimeout(timeout)
    try:
        while True:
            c = sock.recv(4096).decode()
            if not c: break
            buf += c
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line:
                    try: msgs.append(json.loads(line))
                    except: pass
    except socket.timeout: pass
    return msgs

def client(name):
    s = socket.socket()
    s.connect((HOST, PORT))
    send(s, {"username": name})
    recv(s, .5)
    return s

def show(msgs, prefix=""):
    for m in msgs:
        t = m.get("type")
        if t == "ok":      print(f"  {prefix}✔  {m.get('message')}")
        elif t == "error": print(f"  {prefix}✘  {m.get('message')}")
        elif t == "new_bid":
            print(f"  {prefix}💰 [{m.get('item_name')}] {m.get('bidder')} → R${float(m.get('amount',0)):.2f}")
        elif t == "auction_end":
            w = m.get("winner")
            print(f"  {prefix}🏆 [{m.get('item_name')}] Vencedor: {w or 'nenhum'} R${float(m.get('winning_amount',0)):.2f}")
        elif t == "auction_start":
            print(f"  {prefix}🔔 Leilão aberto: «{m.get('name')}» por {m.get('owner')}")

def wait_server(t=10):
    t0 = time.time()
    while time.time()-t0 < t:
        try:
            s=socket.socket(); s.settimeout(1); s.connect((HOST,PORT)); s.close(); return True
        except: time.sleep(.4)
    return False

SEP = "─"*58

def main():
    print("\n" + "═"*58)
    print("  🎪 DEMO v2 — MÚLTIPLOS LEILÕES SIMULTÂNEOS")
    print("═"*58)

    proc = subprocess.Popen([sys.executable,"auction_server.py"],
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    time.sleep(1)
    if not wait_server():
        print("[ERRO] Servidor não iniciou."); proc.terminate(); sys.exit(1)
    print("[OK] Servidor pronto.\n")

    try:
        # ── Clientes ──────────────────────────────────────────────────────────
        alice = client("alice")
        bob   = client("bob")
        carol = client("carol")
        diana = client("diana")

        # ── 1. Três leilões simultâneos criados por donos diferentes ─────────
        print(SEP)
        print("1. Abrindo três leilões simultâneos…")
        print(SEP)

        send(alice, {"cmd":"register_item","name":"Violão Vintage 1962",
                     "description":"Guitarra acústica rara","starting_price":500})
        show(recv(alice), "alice ")

        send(bob, {"cmd":"register_item","name":"Câmera Leica M6",
                   "description":"35mm analógica, impecável","starting_price":3000})
        show(recv(bob), "bob   ")

        send(carol, {"cmd":"register_item","name":"Relógio Seiko 5",
                     "description":"Automático, caixa aço","starting_price":800})
        show(recv(carol), "carol ")
        time.sleep(.4)

        # ── 2. Listar todos ──────────────────────────────────────────────────
        print(f"\n{SEP}")
        print("2. Diana lista todos os leilões…")
        print(SEP)
        send(diana, {"cmd":"list_items"})
        msgs = recv(diana)
        for m in msgs:
            if m.get("type") == "item_list":
                items = m.get("items",[])
                for it in items:
                    print(f"  📋 {it['item_id'][-8:]}  «{it['name']}»  dono:{it['owner']}  R${it['starting_price']:.2f}")
                item_ids = [it["item_id"] for it in items]
        time.sleep(.2)

        # ── 3. Lances cruzados (vários usuários, vários leilões) ─────────────
        print(f"\n{SEP}")
        print("3. Lances cruzados em leilões diferentes…")
        print(SEP)

        violao_id = next(i["item_id"] for i in items if "Viol" in i["name"])
        camera_id = next(i["item_id"] for i in items if "Leica" in i["name"])
        relogio_id= next(i["item_id"] for i in items if "Seiko" in i["name"])

        lances = [
            (bob,   violao_id, 600,  "bob no violão"),
            (diana, violao_id, 750,  "diana no violão"),
            (alice, camera_id, 3200, "alice na câmera (erro: dono é bob)"),
            (diana, camera_id, 3200, "diana na câmera"),
            (bob,   camera_id, 3500, "bob na câmera (erro: dono é bob)"),
            (alice, relogio_id,900,  "alice no relógio"),
            (diana, relogio_id,950,  "diana no relógio"),
            (bob,   violao_id, 800,  "bob supera diana no violão"),
            (carol, camera_id, 3600, "carol na câmera"),
            (alice, relogio_id,1000, "alice supera diana no relógio"),
        ]
        for sock, iid, amt, desc in lances:
            send(sock, {"cmd":"bid","item_id":iid,"amount":amt})
            msgs = recv(sock, .8)
            for m in msgs:
                if m.get("type") in ("ok","error"):
                    icon = "✔" if m["type"]=="ok" else "✘"
                    print(f"  {icon} {desc}: {m['message']}")
            time.sleep(.2)

        # ── 4. Tentar fechar leilão de outro (deve falhar) ────────────────────
        print(f"\n{SEP}")
        print("4. Bob tenta fechar o relógio (dono: carol) → deve falhar…")
        print(SEP)
        send(bob, {"cmd":"close_auction","item_id":relogio_id})
        show(recv(bob), "bob   ")

        # ── 5. Carol fecha seu próprio leilão ─────────────────────────────────
        print(f"\n{SEP}")
        print("5. Carol fecha seu próprio leilão (relógio)…")
        print(SEP)
        send(carol, {"cmd":"close_auction","item_id":relogio_id})
        show(recv(carol), "carol ")
        time.sleep(.4)
        # Coleta notificação broadcast
        show(recv(alice,.5), "alice← ")
        show(recv(diana,.5), "diana← ")

        # ── 6. Alice fecha o violão ───────────────────────────────────────────
        print(f"\n{SEP}")
        print("6. Alice fecha o violão…")
        print(SEP)
        send(alice, {"cmd":"close_auction","item_id":violao_id})
        show(recv(alice), "alice ")
        time.sleep(.3)

        # ── 7. Bob fecha a câmera ─────────────────────────────────────────────
        print(f"\n{SEP}")
        print("7. Bob fecha a câmera…")
        print(SEP)
        send(bob, {"cmd":"close_auction","item_id":camera_id})
        show(recv(bob), "bob   ")

    finally:
        time.sleep(.5)
        proc.terminate()

    print(f"\n{'═'*58}")
    print("  ✅ DEMO CONCLUÍDA")
    print("  📄 Histórico: auction_log.json")
    print("═"*58 + "\n")

if __name__ == "__main__":
    main()