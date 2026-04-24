import React, { useState } from 'react'
import { useAuction } from '../context/Auctioncontext'
import type { AuctionItem } from '../types/Index'
import logoUrl from '../assets/dayfox-logo.webp'

export default function AdminPage() {
  const { items, send, currentUser, logout, connected, logs } = useAuction()
  const [itemName, setItemName] = useState('')
  const [itemDesc, setItemDesc] = useState('')
  const [startingPrice, setStartingPrice] = useState('')
  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState('')

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(''); setFormSuccess('')
    const name = itemName.trim()
    const price = parseFloat(startingPrice)
    if (!name) { setFormError('Nome do item é obrigatório.'); return }
    if (isNaN(price) || price <= 0) { setFormError('Preço inicial deve ser maior que zero.'); return }
    send('ADD_ITEM', { name, description: itemDesc.trim(), starting_price: price })
    setItemName(''); setItemDesc(''); setStartingPrice('')
    setFormSuccess('Item cadastrado com sucesso!')
    setTimeout(() => setFormSuccess(''), 3000)
  }

  const handleClose = (itemId: string) => {
    if (!window.confirm('Deseja encerrar este leilão?')) return
    send('CLOSE_AUCTION', { item_id: itemId })
  }

  const activeItems = items.filter((i) => i.is_active)
  const closedItems = items.filter((i) => !i.is_active)

  return (
    <div style={s.layout}>
      {/* ── Sidebar ── */}
      <aside style={s.sidebar}>
        <div style={s.sideTop}>
          <img src={logoUrl} alt="DayFox" style={s.sideLogoImg} />
        </div>

        <div style={s.userCard}>
          <div style={s.userAvatar}>{currentUser?.name[0].toUpperCase()}</div>
          <div>
            <div style={s.userName}>{currentUser?.name}</div>
            <div style={s.userRole}>Administrador</div>
          </div>
          <div style={{ ...s.connDot, background: connected ? '#22c55e' : '#ef4444' }} />
        </div>

        <div style={s.statsRow}>
          <div style={s.statBox}>
            <span style={s.statNum}>{activeItems.length}</span>
            <span style={s.statLabel}>Ativos</span>
          </div>
          <div style={s.statBox}>
            <span style={s.statNum}>{closedItems.length}</span>
            <span style={s.statLabel}>Encerrados</span>
          </div>
        </div>

        <div style={{ flex: 1 }} />
        <button onClick={logout} style={s.logoutBtn}>Sair</button>
      </aside>

      {/* ── Main ── */}
      <main style={s.main}>
        {/* Cadastrar Item */}
        <section style={s.section}>
          <h2 style={s.sectionTitle}>Cadastrar Novo Item</h2>
          <div style={s.formCard}>
            <form onSubmit={handleAddItem}>
              <div style={s.formRow}>
                <div style={s.field}>
                  <label style={s.label}>Nome do Item *</label>
                  <input style={s.input} placeholder="Ex: Violão Giannini" value={itemName}
                    onChange={(e) => setItemName(e.target.value)} maxLength={80} />
                </div>
                <div style={{ ...s.field, maxWidth: 180 }}>
                  <label style={s.label}>Preço Inicial (R$) *</label>
                  <input style={s.input} type="number" placeholder="500.00"
                    min="0.01" step="0.01" value={startingPrice}
                    onChange={(e) => setStartingPrice(e.target.value)} />
                </div>
              </div>
              <div style={s.field}>
                <label style={s.label}>Descrição</label>
                <textarea style={{ ...s.input, resize: 'vertical', minHeight: 68 }}
                  placeholder="Descreva o item..."
                  value={itemDesc} onChange={(e) => setItemDesc(e.target.value)} maxLength={300} />
              </div>
              {formError && <p style={s.error}>{formError}</p>}
              {formSuccess && <p style={s.success}>{formSuccess}</p>}
              <button type="submit" style={s.primaryBtn}>+ Cadastrar Item</button>
            </form>
          </div>
        </section>

        {/* Leilões Ativos */}
        <section style={s.section}>
          <h2 style={s.sectionTitle}>Leilões Ativos</h2>
          {activeItems.length === 0
            ? <p style={s.empty}>Nenhum leilão ativo. Cadastre um item acima!</p>
            : <div style={s.grid}>{activeItems.map((item) => <ItemCard key={item.item_id} item={item} onClose={handleClose} isAdmin />)}</div>}
        </section>

        {closedItems.length > 0 && (
          <section style={s.section}>
            <h2 style={s.sectionTitle}>Leilões Encerrados</h2>
            <div style={s.grid}>{closedItems.map((item) => <ItemCard key={item.item_id} item={item} isAdmin />)}</div>
          </section>
        )}

        {/* Log */}
        <section style={s.section}>
          <h2 style={s.sectionTitle}>Log de Eventos</h2>
          <LogPanel logs={logs} />
        </section>
      </main>
    </div>
  )
}

// ── ItemCard ──────────────────────────────────────────────────────

function ItemCard({ item, onClose, isAdmin }: { item: AuctionItem; onClose?: (id: string) => void; isAdmin?: boolean }) {
  return (
    <div style={{ ...s.card, borderTop: item.is_active ? '4px solid #E8651A' : '4px solid #d1d5db' }}>
      <div style={s.cardHeader}>
        <span style={s.cardId}>#{item.item_id}</span>
        <span style={{ ...s.badge, background: item.is_active ? '#fff3e0' : '#f3f4f6', color: item.is_active ? '#C4420F' : '#6b7280' }}>
          {item.is_active ? '● Ativo' : '○ Encerrado'}
        </span>
      </div>
      <h3 style={s.cardName}>{item.name}</h3>
      {item.description && <p style={s.cardDesc}>{item.description}</p>}
      <div style={s.priceRow}>
        <div>
          <span style={s.priceLabel}>Inicial</span>
          <span style={s.priceVal}>R$ {item.starting_price.toFixed(2)}</span>
        </div>
        <div>
          <span style={s.priceLabel}>Lance atual</span>
          <span style={{ ...s.priceVal, color: '#E8651A', fontSize: 18, fontWeight: 800 }}>
            R$ {item.current_price.toFixed(2)}
          </span>
        </div>
      </div>
      {item.current_winner && (
        <p style={s.winner}>🏆 Líder: <strong>{item.current_winner}</strong></p>
      )}
      {isAdmin && item.is_active && onClose && (
        <button onClick={() => onClose(item.item_id)} style={s.closeBtn}>Encerrar Leilão</button>
      )}
    </div>
  )
}

// ── LogPanel ──────────────────────────────────────────────────────

function LogPanel({ logs }: { logs: ReturnType<typeof useAuction>['logs'] }) {
  const colors: Record<string, string> = {
    BID_ACCEPTED: '#22c55e', BID_REJECTED: '#ef4444',
    AUCTION_CLOSED: '#F5A623', ITEM_ADDED: '#60a5fa',
    ERROR: '#ef4444', INFO: '#94a3b8',
  }
  return (
    <div style={s.logBox}>
      {logs.length === 0
        ? <p style={{ color: '#8B5E3C', padding: 12, opacity: 0.6 }}>Aguardando eventos…</p>
        : logs.map((log) => (
          <div key={log.id} style={s.logEntry}>
            <span style={s.logTime}>{log.timestamp}</span>
            <span style={{ ...s.logType, color: colors[log.type] ?? '#94a3b8' }}>[{log.type}]</span>
            <span style={s.logMsg}>{log.message}</span>
          </div>
        ))}
    </div>
  )
}

export { ItemCard, LogPanel }

// ── Estilos ───────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  layout: { display: 'flex', minHeight: '100vh', background: '#FFF8F0', fontFamily: "'Nunito', sans-serif" },

  // Sidebar
  sidebar: { width: 230, background: '#52290a', color: '#fff', display: 'flex', flexDirection: 'column', padding: '20px 16px', gap: 16, flexShrink: 0 },
  sideTop: { display: 'flex', justifyContent: 'center', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.08)' },
  sideLogoImg: { width: 130, height: 'auto', objectFit: 'contain' },
  userCard: { display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(255,255,255,0.07)', borderRadius: 10, padding: '10px 12px' },
  userAvatar: { width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg,#E8651A,#F5A623)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16, flexShrink: 0 },
  userName: { fontSize: 14, fontWeight: 700, lineHeight: 1.2 },
  userRole: { fontSize: 11, color: '#F5A623', fontWeight: 600 },
  connDot: { width: 9, height: 9, borderRadius: '50%', marginLeft: 'auto', flexShrink: 0 },
  statsRow: { display: 'flex', gap: 8 },
  statBox: { flex: 1, background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: '10px 8px', textAlign: 'center' },
  statNum: { display: 'block', fontSize: 22, fontWeight: 800, color: '#F5A623' },
  statLabel: { fontSize: 11, color: '#c4a882' },
  logoutBtn: { background: 'none', border: '1px solid rgba(255,255,255,0.15)', color: '#c4a882', borderRadius: 8, padding: '9px', cursor: 'pointer', fontSize: 13, fontFamily: "'Nunito', sans-serif", fontWeight: 600 },

  // Main
  main: { flex: 1, padding: '28px 32px', overflowY: 'auto', maxWidth: 1100 },
  section: { marginBottom: 36 },
  sectionTitle: { fontSize: 18, fontWeight: 800, color: '#1C1107', marginBottom: 16, paddingBottom: 10, borderBottom: '2px solid #F0D9C8', fontFamily: "'Nunito', sans-serif" },

  // Form
  formCard: { background: '#fff', borderRadius: 14, padding: 24, boxShadow: '0 2px 12px rgba(196,66,15,0.07)' },
  formRow: { display: 'flex', gap: 16, flexWrap: 'wrap' },
  field: { flex: 1, minWidth: 180, marginBottom: 14 },
  label: { display: 'block', fontSize: 13, fontWeight: 700, color: '#1C1107', marginBottom: 5 },
  input: { width: '100%', padding: '10px 12px', border: '2px solid #F0D9C8', borderRadius: 8, fontSize: 14, outline: 'none', fontFamily: "'Nunito', sans-serif", color: '#1C1107', boxSizing: 'border-box' },
  error: { color: '#C0392B', fontSize: 13, marginBottom: 8, fontWeight: 600 },
  success: { color: '#2D9C4A', fontSize: 13, marginBottom: 8, fontWeight: 600 },
  primaryBtn: { padding: '11px 28px', background: 'linear-gradient(135deg,#E8651A,#C4420F)', color: '#fff', border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 800, cursor: 'pointer', fontFamily: "'Nunito', sans-serif", boxShadow: '0 3px 12px rgba(196,66,15,0.25)' },

  // Grid & Cards
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 },
  card: { background: '#fff', borderRadius: 12, padding: 18, boxShadow: '0 2px 10px rgba(196,66,15,0.07)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  cardId: { fontSize: 11, color: '#8B5E3C', fontFamily: 'monospace', fontWeight: 700 },
  badge: { fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20 },
  cardName: { fontSize: 16, fontWeight: 800, color: '#1C1107', marginBottom: 4 },
  cardDesc: { fontSize: 13, color: '#8B5E3C', marginBottom: 12 },
  priceRow: { display: 'flex', gap: 20, marginBottom: 10 },
  priceLabel: { display: 'block', fontSize: 11, color: '#8B5E3C', marginBottom: 2 },
  priceVal: { display: 'block', fontSize: 15, fontWeight: 700, color: '#1C1107' },
  winner: { fontSize: 13, color: '#1C1107', marginBottom: 10 },
  closeBtn: { width: '100%', padding: '9px', background: '#C0392B', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: "'Nunito', sans-serif", marginTop: 4 },
  empty: { color: '#8B5E3C', fontSize: 14, opacity: 0.7 },

  // Log
  logBox: { background: '#1C1107', borderRadius: 10, padding: '12px 16px', maxHeight: 280, overflowY: 'auto', fontFamily: 'monospace' },
  logEntry: { display: 'flex', gap: 10, fontSize: 12, padding: '5px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', flexWrap: 'wrap' },
  logTime: { color: '#8B5E3C', flexShrink: 0 },
  logType: { fontWeight: 700, flexShrink: 0 },
  logMsg: { color: '#e2cdb8', wordBreak: 'break-word' },
}