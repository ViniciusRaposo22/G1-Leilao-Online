#!/usr/bin/env python3
"""
Monitor Web do Leilão v2 — bridge TCP → WebSocket → HTML
Exibe todos os leilões simultâneos em tempo real.
"""

import socket, threading, json, time, http.server, socketserver
import hashlib, base64, struct, datetime

TCP_HOST    = "127.0.0.1"
TCP_PORT    = 9000
WEB_PORT    = 8080
MONITOR_USR = "__monitor__"

state_lock  = threading.Lock()
ws_clients  = []
auctions    = {}   # item_id → dict
feed        = []

# ─── WebSocket helpers ────────────────────────────────────────────────────────
def ws_handshake(conn):
    data = conn.recv(4096).decode()
    key  = next((l.split(": ")[1].strip() for l in data.split("\r\n")
                 if "Sec-WebSocket-Key" in l), None)
    if not key: return False
    magic  = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    accept = base64.b64encode(hashlib.sha1((key+magic).encode()).digest()).decode()
    conn.sendall((
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    ).encode())
    return True

def ws_frame(msg):
    p = msg.encode()
    n = len(p)
    h = (struct.pack("BB", 0x81, n) if n<=125 else
         struct.pack("!BBH", 0x81, 126, n) if n<=65535 else
         struct.pack("!BBQ", 0x81, 127, n))
    return h + p

def ws_broadcast(msg):
    raw  = ws_frame(json.dumps(msg))
    dead = []
    with state_lock:
        targets = list(ws_clients)
    for c in targets:
        try: c.sendall(raw)
        except Exception: dead.append(c)
    for c in dead:
        try: ws_clients.remove(c)
        except Exception: pass

def handle_ws(conn, addr):
    if not ws_handshake(conn): conn.close(); return
    with state_lock:
        ws_clients.append(conn)
        snap  = {k: dict(v) for k, v in auctions.items()}
        recent= list(feed[-50:])
    try:
        conn.sendall(ws_frame(json.dumps({"type":"init","auctions":snap,"feed":recent})))
        while True:
            if not conn.recv(256): break
    except Exception: pass
    finally:
        try: ws_clients.remove(conn)
        except Exception: pass
        conn.close()

# ─── TCP bridge ───────────────────────────────────────────────────────────────
def now_ts():
    return datetime.datetime.now().strftime("%H:%M:%S")

def add_feed(entry):
    with state_lock:
        feed.append(entry)
        if len(feed) > 300: feed.pop(0)

def process(msg):
    t  = msg.get("type")
    ts = now_ts()

    if t == "item_list":
        with state_lock:
            for it in msg.get("items", []):
                auctions[it["item_id"]] = it
        ws_broadcast({"type":"full_update","auctions":dict(auctions)})

    elif t == "auction_start":
        it = {k: msg.get(k) for k in
              ("item_id","name","description","starting_price","owner","status")}
        it["current_bid"] = 0; it["current_bidder"] = ""; it["bid_count"] = 0
        it["status"] = "open"
        with state_lock:
            auctions[it["item_id"]] = it
        entry = {"ts":ts,"type":"start",
                 "text":f"🔔 {msg.get('owner')} abriu «{msg.get('name')}» — R${float(msg.get('starting_price',0)):.2f}",
                 "item_id": it["item_id"]}
        add_feed(entry)
        ws_broadcast({"type":"auction_start","item":it,"feed_entry":entry})

    elif t == "new_bid":
        iid = msg.get("item_id")
        with state_lock:
            if iid in auctions:
                auctions[iid]["current_bid"]    = msg.get("amount")
                auctions[iid]["current_bidder"] = msg.get("bidder")
                auctions[iid]["bid_count"]      = msg.get("bid_count",0)
                snap = dict(auctions[iid])
            else:
                snap = {}
        entry = {"ts":ts,"type":"bid",
                 "text":f"💰 [{msg.get('item_name')}] {msg.get('bidder')} → R${float(msg.get('amount',0)):.2f}",
                 "item_id":iid,"bidder":msg.get("bidder"),"amount":msg.get("amount")}
        add_feed(entry)
        ws_broadcast({"type":"bid_update","item_id":iid,"item":snap,"feed_entry":entry})

    elif t == "auction_end":
        iid = msg.get("item_id")
        with state_lock:
            if iid in auctions:
                auctions[iid]["status"] = "closed"
                snap = dict(auctions[iid])
            else:
                snap = {}
        entry = {"ts":ts,"type":"end",
                 "text":f"🏆 [{msg.get('item_name')}] Vencedor: {msg.get('winner') or 'nenhum'} — R${float(msg.get('winning_amount',0)):.2f}",
                 "item_id":iid}
        add_feed(entry)
        ws_broadcast({"type":"auction_end","item_id":iid,"item":snap,
                      "winner":msg.get("winner"),"amount":msg.get("winning_amount"),
                      "feed_entry":entry})

    elif t == "notice":
        entry = {"ts":ts,"type":"notice","text":msg.get("message","")}
        add_feed(entry)
        ws_broadcast({"type":"feed_entry","entry":entry})


def tcp_receiver():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_HOST, TCP_PORT))
            sock.sendall((json.dumps({"username": MONITOR_USR}) + "\n").encode())
            print(f"[TCP] Conectado ao servidor {TCP_HOST}:{TCP_PORT}")
            buf = ""
            while True:
                chunk = sock.recv(4096).decode()
                if not chunk: break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        try: process(json.loads(line))
                        except Exception: pass
        except Exception as e:
            print(f"[TCP] Desconectado ({e}). Reconectando em 3s…")
            time.sleep(3)

# ─── HTML ─────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Leilão Eletrônico — Painel</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Mono:wght@400;500&family=Figtree:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#07070d;--s1:#0e0e1a;--s2:#141424;
  --bdr:#1f1f35;--bdr2:#2a2a45;
  --gold:#e8b84b;--gold2:#ffd166;
  --grn:#3dd68c;--red:#ff6b6b;--blu:#60a5fa;
  --pur:#a78bfa;--ora:#fb923c;
  --txt:#dde1f0;--mut:#5a5a80;--dim:#3a3a58;
  --fn-display:'Syne',sans-serif;
  --fn-mono:'IBM Plex Mono',monospace;
  --fn-body:'Figtree',sans-serif;
}
body{background:var(--bg);color:var(--txt);font-family:var(--fn-body);min-height:100vh;overflow-x:hidden}

/* noise */
body::after{content:'';position:fixed;inset:0;
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.04'/%3E%3C/svg%3E");
  pointer-events:none;z-index:0}

/* ── Header ── */
header{
  position:sticky;top:0;z-index:200;
  border-bottom:1px solid var(--bdr);
  background:rgba(7,7,13,.88);
  backdrop-filter:blur(16px);
  padding:.9rem 1.8rem;
  display:flex;align-items:center;gap:1rem;
}
.logo{font-family:var(--fn-display);font-size:1.4rem;font-weight:800;
  background:linear-gradient(135deg,var(--gold),var(--ora));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hdr-right{margin-left:auto;display:flex;align-items:center;gap:1rem}
.live-badge{display:flex;align-items:center;gap:.4rem;
  font-family:var(--fn-mono);font-size:.68rem;color:var(--mut);
  text-transform:uppercase;letter-spacing:.1em}
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--mut);transition:background .3s}
.live-dot.on{background:var(--grn);box-shadow:0 0 8px var(--grn);animation:blink 1.4s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}
#auction-count{font-family:var(--fn-mono);font-size:.75rem;color:var(--mut)}

/* ── Layout ── */
.layout{display:grid;grid-template-columns:1fr 340px;gap:0;min-height:calc(100vh - 53px);position:relative;z-index:1}
@media(max-width:860px){.layout{grid-template-columns:1fr}}

/* ── Main panel ── */
.main-panel{padding:1.6rem;border-right:1px solid var(--bdr)}

.section-title{
  font-family:var(--fn-mono);font-size:.65rem;text-transform:uppercase;
  letter-spacing:.18em;color:var(--mut);margin-bottom:1rem;
  display:flex;align-items:center;gap:.6rem;
}
.section-title::after{content:'';flex:1;height:1px;background:var(--bdr)}

/* ── Auction grid ── */
#auction-grid{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
  gap:1rem;
}

.auction-card{
  background:var(--s1);
  border:1px solid var(--bdr);
  border-radius:14px;
  padding:1.25rem;
  position:relative;
  overflow:hidden;
  transition:border-color .2s,transform .2s;
  cursor:default;
  animation:cardIn .3s ease;
}
@keyframes cardIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.auction-card:hover{border-color:var(--bdr2);transform:translateY(-2px)}
.auction-card.closed{opacity:.55;filter:grayscale(.6)}

/* glow top border */
.auction-card::before{
  content:'';position:absolute;top:0;left:10%;right:10%;height:1px;
  background:linear-gradient(90deg,transparent,var(--gold),transparent);
  opacity:.5;
}
.auction-card.closed::before{opacity:.15}

.card-owner{
  font-family:var(--fn-mono);font-size:.65rem;color:var(--mut);
  text-transform:uppercase;letter-spacing:.08em;margin-bottom:.4rem;
  display:flex;align-items:center;gap:.4rem;
}
.owner-badge{background:var(--pur);color:#fff;font-size:.55rem;
  padding:.1rem .4rem;border-radius:20px;font-weight:600}

.card-name{
  font-family:var(--fn-display);font-size:1.15rem;font-weight:800;
  line-height:1.2;margin-bottom:.3rem;color:var(--txt);
}
.card-desc{font-size:.8rem;color:var(--mut);margin-bottom:1rem;line-height:1.5}

.bid-row{
  background:var(--s2);border:1px solid var(--bdr);border-radius:10px;
  padding:.85rem 1rem;display:flex;align-items:center;gap:.75rem;
  margin-bottom:.85rem;
}
.bid-val{
  font-family:var(--fn-display);font-size:1.6rem;font-weight:800;
  color:var(--gold2);line-height:1;flex:1;
  transition:color .3s;
}
.bid-row.flash .bid-val{color:var(--grn)}
.bid-meta{font-family:var(--fn-mono);font-size:.65rem;color:var(--mut);text-align:right}
.bid-meta span{color:var(--gold);display:block}

.card-footer{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
.badge{
  font-family:var(--fn-mono);font-size:.62rem;padding:.25rem .65rem;
  border-radius:20px;border:1px solid;
}
.badge-open{border-color:var(--grn);color:var(--grn)}
.badge-closed{border-color:var(--red);color:var(--red)}
.badge-bids{border-color:var(--bdr2);color:var(--mut)}
.badge-start{border-color:var(--bdr2);color:var(--mut)}

/* Winner overlay */
.winner-overlay{
  position:absolute;inset:0;border-radius:14px;
  background:linear-gradient(135deg,rgba(55,30,90,.97),rgba(20,15,40,.97));
  border:1px solid var(--pur);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:.5rem;text-align:center;padding:1.5rem;
  animation:fadeIn .4s ease;
}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.winner-overlay .trophy{font-size:2rem}
.winner-overlay h3{font-family:var(--fn-display);font-size:1rem;color:var(--gold2)}
.winner-overlay p{font-size:.85rem;color:var(--mut)}
.winner-overlay .wname{color:var(--blu);font-weight:600}
.winner-overlay .wamt{color:var(--gold2);font-size:1.1rem;font-weight:700;font-family:var(--fn-mono)}

/* Empty state */
.empty-state{
  grid-column:1/-1;text-align:center;padding:4rem 2rem;color:var(--mut);
}
.empty-state .icon{font-size:3rem;margin-bottom:1rem}
.empty-state p{font-size:.95rem}

/* ── Sidebar feed ── */
.side-panel{
  display:flex;flex-direction:column;
  border-left:1px solid var(--bdr);
  background:var(--s1);
  max-height:calc(100vh - 53px);
  position:sticky;top:53px;
}
.feed-header{
  padding:1rem 1.2rem .75rem;
  border-bottom:1px solid var(--bdr);
  font-family:var(--fn-mono);font-size:.65rem;
  text-transform:uppercase;letter-spacing:.15em;color:var(--mut);
}
#feed-list{
  flex:1;overflow-y:auto;padding:.75rem;
  display:flex;flex-direction:column;gap:.4rem;
  scrollbar-width:thin;scrollbar-color:var(--bdr) transparent;
}
.feed-item{
  padding:.55rem .7rem;border-radius:8px;border-left:2px solid transparent;
  font-size:.78rem;line-height:1.45;
  animation:slideIn .2s ease;
}
@keyframes slideIn{from{opacity:0;transform:translateX(6px)}to{opacity:1}}
.feed-item.bid   {border-color:var(--grn);background:rgba(61,214,140,.05)}
.feed-item.start {border-color:var(--gold);background:rgba(232,184,75,.05)}
.feed-item.end   {border-color:var(--pur);background:rgba(167,139,250,.06)}
.feed-item.notice{border-color:var(--bdr);background:transparent;color:var(--mut)}
.feed-ts{font-family:var(--fn-mono);font-size:.62rem;color:var(--dim);margin-bottom:.15rem}
.feed-txt{color:var(--txt)}
.feed-item.notice .feed-txt{color:var(--mut)}

/* conn bar */
#conn{
  position:fixed;bottom:1rem;right:1rem;z-index:300;
  background:var(--s2);border:1px solid var(--bdr);border-radius:20px;
  padding:.35rem .9rem;display:flex;align-items:center;gap:.5rem;
  font-family:var(--fn-mono);font-size:.65rem;color:var(--mut);
}
#cdot{width:6px;height:6px;border-radius:50%;background:var(--mut)}
#cdot.on{background:var(--grn);box-shadow:0 0 4px var(--grn)}
</style>
</head>
<body>

<header>
  <div class="logo">🔨 Leilão Eletrônico</div>
  <div class="hdr-right">
    <div id="auction-count" class="auction-count"></div>
    <div class="live-badge"><div class="live-dot" id="ldot"></div><span id="lstatus">conectando</span></div>
  </div>
</header>

<div class="layout">
  <div class="main-panel">
    <div class="section-title">Leilões em Andamento</div>
    <div id="auction-grid">
      <div class="empty-state">
        <div class="icon">⏳</div>
        <p>Aguardando leilões…</p>
      </div>
    </div>
  </div>

  <div class="side-panel">
    <div class="feed-header">Transmissão ao Vivo</div>
    <div id="feed-list"></div>
  </div>
</div>

<div id="conn"><div id="cdot"></div><span id="ctxt">conectando…</span></div>

<script>
const fmtBRL = v => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v||0);
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const $ = id => document.getElementById(id);

let auctions = {};   // item_id → item
let ws, reconTimer;

// ── Build / update card ──────────────────────────────────────────────────────
function buildCard(item) {
  const iid    = item.item_id;
  const closed = item.status === 'closed';
  const hasBid = item.current_bid > 0;

  let el = document.getElementById('card-' + iid);
  const isNew = !el;
  if (isNew) {
    el = document.createElement('div');
    el.id = 'card-' + iid;
    el.className = 'auction-card' + (closed ? ' closed' : '');
  }

  if (closed) {
    el.className = 'auction-card closed';
    el.innerHTML = `
      <div class="card-name">${esc(item.name)}</div>
      <div class="winner-overlay">
        <div class="trophy">🏆</div>
        <h3>Leilão Encerrado</h3>
        <p>Vencedor: <span class="wname">${esc(item.winner||item.current_bidder||'—')}</span></p>
        <div class="wamt">${fmtBRL(item.winning_amount||item.current_bid)}</div>
        <p style="margin-top:.25rem;font-size:.7rem">${item.bid_count||0} lances</p>
      </div>`;
  } else {
    el.innerHTML = `
      <div class="card-owner">
        <span>${esc(item.owner)}</span>
        <span class="owner-badge">dono</span>
      </div>
      <div class="card-name">${esc(item.name)}</div>
      <div class="card-desc">${esc(item.description||'')}</div>
      <div class="bid-row" id="bidrow-${iid}">
        <div>
          <div style="font-family:var(--fn-mono);font-size:.58rem;color:var(--mut);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.2rem">Lance atual</div>
          <div class="bid-val">${fmtBRL(item.current_bid)}</div>
        </div>
        <div class="bid-meta">
          ${hasBid ? `por<span>${esc(item.current_bidder)}</span>` : '<span style="color:var(--mut)">sem lances</span>'}
        </div>
      </div>
      <div class="card-footer">
        <span class="badge badge-open">● aberto</span>
        <span class="badge badge-bids">${item.bid_count||0} lances</span>
        <span class="badge badge-start">mín R$${(item.starting_price||0).toFixed(2)}</span>
      </div>`;
  }
  return {el, isNew};
}

function renderAll() {
  const grid = $('auction-grid');
  const items = Object.values(auctions);
  // Sort: open first, then by bid count desc
  items.sort((a,b) => {
    if (a.status===b.status) return (b.bid_count||0)-(a.bid_count||0);
    return a.status==='open' ? -1 : 1;
  });

  if (!items.length) {
    grid.innerHTML = `<div class="empty-state"><div class="icon">⏳</div><p>Aguardando leilões…</p></div>`;
    return;
  }

  // Remove empty state
  const emp = grid.querySelector('.empty-state');
  if (emp) emp.remove();

  items.forEach(item => {
    const {el, isNew} = buildCard(item);
    if (isNew) grid.appendChild(el);
  });

  const open = items.filter(i => i.status==='open').length;
  $('auction-count').textContent = `${open} ativo${open!==1?'s':''}  ·  ${items.length} total`;
}

function flashBid(iid) {
  const row = document.getElementById('bidrow-' + iid);
  if (!row) return;
  row.classList.remove('flash');
  void row.offsetWidth;
  row.classList.add('flash');
  setTimeout(() => row.classList.remove('flash'), 600);
}

// ── Feed ─────────────────────────────────────────────────────────────────────
function addFeed(entry) {
  const list = $('feed-list');
  const div  = document.createElement('div');
  div.className = `feed-item ${entry.type||'notice'}`;
  div.innerHTML = `<div class="feed-ts">${esc(entry.ts)}</div><div class="feed-txt">${esc(entry.text)}</div>`;
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
  while (list.children.length > 120) list.removeChild(list.firstChild);
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  const proto = location.protocol==='https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    $('cdot').className = 'on'; $('ctxt').textContent = 'conectado';
    $('ldot').className = 'live-dot on'; $('lstatus').textContent = 'ao vivo';
    clearTimeout(reconTimer);
  };

  ws.onclose = ws.onerror = () => {
    $('cdot').className = ''; $('ctxt').textContent = 'reconectando…';
    $('ldot').className = 'live-dot'; $('lstatus').textContent = 'desconectado';
    reconTimer = setTimeout(connect, 3000);
  };

  ws.onmessage = e => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'init') {
      auctions = msg.auctions || {};
      renderAll();
      (msg.feed||[]).forEach(addFeed);

    } else if (msg.type === 'full_update') {
      auctions = msg.auctions || {};
      renderAll();

    } else if (msg.type === 'auction_start') {
      auctions[msg.item.item_id] = msg.item;
      const grid = $('auction-grid');
      const emp  = grid.querySelector('.empty-state');
      if (emp) emp.remove();
      const {el} = buildCard(msg.item);
      grid.prepend(el);
      if (msg.feed_entry) addFeed(msg.feed_entry);
      const open = Object.values(auctions).filter(i=>i.status==='open').length;
      $('auction-count').textContent = `${open} ativo${open!==1?'s':''}  ·  ${Object.keys(auctions).length} total`;

    } else if (msg.type === 'bid_update') {
      auctions[msg.item_id] = msg.item;
      const {el, isNew} = buildCard(msg.item);
      if (isNew) $('auction-grid').prepend(el);
      flashBid(msg.item_id);
      if (msg.feed_entry) addFeed(msg.feed_entry);

    } else if (msg.type === 'auction_end') {
      if (auctions[msg.item_id]) {
        auctions[msg.item_id].status = 'closed';
        auctions[msg.item_id].winner = msg.winner;
        auctions[msg.item_id].winning_amount = msg.amount;
      }
      const {el, isNew} = buildCard(auctions[msg.item_id]||{item_id:msg.item_id,name:'',status:'closed'});
      if (isNew) $('auction-grid').appendChild(el);
      if (msg.feed_entry) addFeed(msg.feed_entry);

    } else if (msg.type === 'feed_entry') {
      addFeed(msg.entry);
    }
  };
}

connect();
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/ws":
            threading.Thread(target=handle_ws,
                             args=(self.connection, self.client_address),
                             daemon=True).start()
            return
        body = HTML.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def main():
    print("="*55)
    print("   🌐 MONITOR WEB DE LEILÃO v2")
    print(f"   Interface : http://localhost:{WEB_PORT}")
    print(f"   Servidor  : {TCP_HOST}:{TCP_PORT}")
    print("="*55)
    threading.Thread(target=tcp_receiver, daemon=True).start()
    httpd = socketserver.TCPServer(("0.0.0.0", WEB_PORT), Handler)
    httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"[OK] Monitor em http://localhost:{WEB_PORT}\n")
    try: httpd.serve_forever()
    except KeyboardInterrupt: print("\n[INFO] Monitor encerrado.")

if __name__ == "__main__":
    main()