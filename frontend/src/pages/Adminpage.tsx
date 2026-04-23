import React, { useState } from 'react'
import { useAuction } from '../context/Auctioncontext'
import type { AuctionItem } from '../types/Index'

export default function AdminPage() {
  const { items, send, currentUser, logout, connected, logs } = useAuction()

  const [itemName, setItemName] = useState('')
  const [itemDesc, setItemDesc] = useState('')
  const [startingPrice, setStartingPrice] = useState('')
  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState('')

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    const name = itemName.trim()
    const price = parseFloat(startingPrice)

    if (!name) { setFormError('Nome do item é obrigatório.'); return }
    if (isNaN(price) || price <= 0) { setFormError('Preço inicial deve ser maior que zero.'); return }

    send('ADD_ITEM', { name, description: itemDesc.trim(), starting_price: price })
    setItemName('')
    setItemDesc('')
    setStartingPrice('')
    setFormSuccess('Item enviado ao servidor!')
    setTimeout(() => setFormSuccess(''), 3000)
  }

  const handleClose = (itemId: string) => {
    if (!window.confirm('Deseja encerrar este leilão?')) return
    send('CLOSE_AUCTION', { item_id: itemId })
  }

  const activeItems = items.filter((i) => i.is_active)
  const closedItems = items.filter((i) => !i.is_active)

  return (
    <div style={styles.layout}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.sideHeader}>
          <span style={styles.logo}>🔨 LeilãoNet</span>
          <span style={styles.roleTag}>Admin</span>
        </div>

        <div style={styles.userInfo}>
          <span style={styles.userName}>{currentUser?.name}</span>
          <span style={{ ...styles.connDot, backgroundColor: connected ? '#22c55e' : '#ef4444' }} />
        </div>

        <nav style={styles.nav}>
          <span style={styles.navItem}>📦 Cadastrar Item</span>
          <span style={styles.navItem}>🏷 Leilões Ativos ({activeItems.length})</span>
          <span style={styles.navItem}>📋 Log de Eventos</span>
        </nav>

        <button onClick={logout} style={styles.logoutBtn}>Sair</button>
      </aside>

      {/* Main */}
      <main style={styles.main}>
        {/* Cadastrar Item */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>📦 Cadastrar Novo Item</h2>
          <form onSubmit={handleAddItem} style={styles.form}>
            <div style={styles.formRow}>
              <div style={styles.field}>
                <label style={styles.label}>Nome do Item *</label>
                <input
                  style={styles.input}
                  placeholder="Ex: Violão Giannini"
                  value={itemName}
                  onChange={(e) => setItemName(e.target.value)}
                  maxLength={80}
                />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Preço Inicial (R$) *</label>
                <input
                  style={styles.input}
                  type="number"
                  placeholder="500.00"
                  min="0.01"
                  step="0.01"
                  value={startingPrice}
                  onChange={(e) => setStartingPrice(e.target.value)}
                />
              </div>
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Descrição</label>
              <textarea
                style={{ ...styles.input, resize: 'vertical', minHeight: 72 }}
                placeholder="Descreva o item..."
                value={itemDesc}
                onChange={(e) => setItemDesc(e.target.value)}
                maxLength={300}
              />
            </div>
            {formError && <p style={styles.error}>{formError}</p>}
            {formSuccess && <p style={styles.success}>{formSuccess}</p>}
            <button type="submit" style={styles.primaryBtn}>+ Cadastrar Item</button>
          </form>
        </section>

        {/* Leilões Ativos */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>🏷 Leilões Ativos</h2>
          {activeItems.length === 0 ? (
            <p style={styles.empty}>Nenhum leilão ativo no momento.</p>
          ) : (
            <div style={styles.grid}>
              {activeItems.map((item) => (
                <ItemCard key={item.item_id} item={item} onClose={handleClose} isAdmin />
              ))}
            </div>
          )}
        </section>

        {/* Leilões Encerrados */}
        {closedItems.length > 0 && (
          <section style={styles.section}>
            <h2 style={styles.sectionTitle}>✅ Leilões Encerrados</h2>
            <div style={styles.grid}>
              {closedItems.map((item) => (
                <ItemCard key={item.item_id} item={item} isAdmin />
              ))}
            </div>
          </section>
        )}

        {/* Log */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>📋 Log de Eventos</h2>
          <LogPanel logs={logs} />
        </section>
      </main>
    </div>
  )
}

// ── Subcomponentes ───────────────────────────────────────────────

function ItemCard({ item, onClose, isAdmin }: { item: AuctionItem; onClose?: (id: string) => void; isAdmin?: boolean }) {
  return (
    <div style={{ ...styles.card, borderLeft: item.is_active ? '4px solid #2563eb' : '4px solid #9ca3af' }}>
      <div style={styles.cardHeader}>
        <span style={styles.cardId}>#{item.item_id}</span>
        <span style={{ ...styles.cardStatus, backgroundColor: item.is_active ? '#dbeafe' : '#f3f4f6', color: item.is_active ? '#1d4ed8' : '#6b7280' }}>
          {item.is_active ? 'Ativo' : 'Encerrado'}
        </span>
      </div>
      <h3 style={styles.cardName}>{item.name}</h3>
      {item.description && <p style={styles.cardDesc}>{item.description}</p>}
      <div style={styles.cardPrices}>
        <div>
          <span style={styles.priceLabel}>Lance inicial</span>
          <span style={styles.priceValue}>R$ {item.starting_price.toFixed(2)}</span>
        </div>
        <div>
          <span style={styles.priceLabel}>Lance atual</span>
          <span style={{ ...styles.priceValue, color: '#2563eb', fontWeight: 700 }}>
            R$ {item.current_price.toFixed(2)}
          </span>
        </div>
      </div>
      {item.current_winner && (
        <p style={styles.winner}>🏆 Líder: <strong>{item.current_winner}</strong></p>
      )}
      {isAdmin && item.is_active && onClose && (
        <button onClick={() => onClose(item.item_id)} style={styles.closeBtn}>
          Encerrar Leilão
        </button>
      )}
    </div>
  )
}

function LogPanel({ logs }: { logs: ReturnType<typeof useAuction>['logs'] }) {
  const colors: Record<string, string> = {
    BID_ACCEPTED: '#166534',
    BID_REJECTED: '#991b1b',
    AUCTION_CLOSED: '#92400e',
    ITEM_ADDED: '#1e40af',
    ERROR: '#dc2626',
    INFO: '#374151',
  }
  return (
    <div style={styles.logBox}>
      {logs.length === 0 ? (
        <p style={{ color: '#9ca3af', padding: 12 }}>Aguardando eventos…</p>
      ) : (
        logs.map((log) => (
          <div key={log.id} style={styles.logEntry}>
            <span style={styles.logTime}>{log.timestamp}</span>
            <span style={{ ...styles.logType, color: colors[log.type] ?? '#374151' }}>[{log.type}]</span>
            <span style={styles.logMsg}>{log.message}</span>
          </div>
        ))
      )}
    </div>
  )
}

// ── Estilos ──────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  layout: { display: 'flex', minHeight: '100vh', backgroundColor: '#f9fafb' },
  sidebar: { width: 220, backgroundColor: '#1e293b', color: '#fff', display: 'flex', flexDirection: 'column', padding: 20, gap: 16, flexShrink: 0 },
  sideHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logo: { fontWeight: 700, fontSize: 18 },
  roleTag: { backgroundColor: '#f59e0b', color: '#1f2937', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700 },
  userInfo: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#334155', borderRadius: 8, padding: '8px 12px' },
  userName: { fontSize: 14, fontWeight: 600 },
  connDot: { width: 10, height: 10, borderRadius: '50%', flexShrink: 0 },
  nav: { display: 'flex', flexDirection: 'column', gap: 4, flex: 1 },
  navItem: { padding: '8px 10px', borderRadius: 6, fontSize: 13, color: '#cbd5e1', cursor: 'default' },
  logoutBtn: { background: 'none', border: '1px solid #475569', color: '#94a3b8', borderRadius: 6, padding: '8px', cursor: 'pointer', fontSize: 13 },
  main: { flex: 1, padding: 28, overflowY: 'auto', maxWidth: 1000 },
  section: { marginBottom: 32 },
  sectionTitle: { fontSize: 18, fontWeight: 700, color: '#1f2937', marginBottom: 14, borderBottom: '2px solid #e5e7eb', paddingBottom: 8 },
  form: {},
  formRow: { display: 'flex', gap: 16, flexWrap: 'wrap' },
  field: { flex: 1, minWidth: 200, marginBottom: 14 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 5 },
  input: { width: '100%', padding: '9px 12px', border: '1.5px solid #d1d5db', borderRadius: 7, fontSize: 14, outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit' },
  error: { color: '#dc2626', fontSize: 13, marginBottom: 8 },
  success: { color: '#16a34a', fontSize: 13, marginBottom: 8 },
  primaryBtn: { padding: '10px 24px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 7, fontSize: 14, fontWeight: 600, cursor: 'pointer' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 18, boxShadow: '0 1px 6px rgba(0,0,0,0.08)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  cardId: { fontSize: 11, color: '#9ca3af', fontFamily: 'monospace' },
  cardStatus: { fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20 },
  cardName: { fontSize: 16, fontWeight: 700, color: '#1f2937', margin: '0 0 6px' },
  cardDesc: { fontSize: 13, color: '#6b7280', marginBottom: 12 },
  cardPrices: { display: 'flex', gap: 20, marginBottom: 10 },
  priceLabel: { display: 'block', fontSize: 11, color: '#9ca3af' },
  priceValue: { fontSize: 15, fontWeight: 600, color: '#1f2937' },
  winner: { fontSize: 13, color: '#374151', marginBottom: 12 },
  closeBtn: { width: '100%', padding: '8px', backgroundColor: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', marginTop: 4 },
  empty: { color: '#9ca3af', fontSize: 14 },
  logBox: { backgroundColor: '#1e293b', borderRadius: 8, padding: 12, maxHeight: 280, overflowY: 'auto', fontFamily: 'monospace' },
  logEntry: { display: 'flex', gap: 10, fontSize: 12, padding: '4px 0', borderBottom: '1px solid #334155', flexWrap: 'wrap' },
  logTime: { color: '#64748b', flexShrink: 0 },
  logType: { fontWeight: 700, flexShrink: 0 },
  logMsg: { color: '#e2e8f0', wordBreak: 'break-word' },
}

export { ItemCard, LogPanel }