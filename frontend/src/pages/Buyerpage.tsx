import React, { useState } from 'react'
import { useAuction } from '../context/Auctioncontext'
import { LogPanel } from './Adminpage'
import type { AuctionItem } from '../types/Index'

export default function BuyerPage() {
  const { items, send, currentUser, logout, connected, logs } = useAuction()
  const [bidAmounts, setBidAmounts] = useState<Record<string, string>>({})
  const [bidErrors, setBidErrors] = useState<Record<string, string>>({})
  const [bidSuccess, setBidSuccess] = useState<Record<string, string>>({})
  const [activeTab, setActiveTab] = useState<'active' | 'closed'>('active')

  const activeItems = items.filter((i) => i.is_active)
  const closedItems = items.filter((i) => !i.is_active)

  const handleBid = (item: AuctionItem) => {
    const raw = bidAmounts[item.item_id] ?? ''
    const amount = parseFloat(raw)

    setBidErrors((prev) => ({ ...prev, [item.item_id]: '' }))
    setBidSuccess((prev) => ({ ...prev, [item.item_id]: '' }))

    if (!raw || isNaN(amount) || amount <= 0) {
      setBidErrors((prev) => ({ ...prev, [item.item_id]: 'Informe um valor válido.' }))
      return
    }
    if (amount <= item.current_price) {
      setBidErrors((prev) => ({
        ...prev,
        [item.item_id]: `Lance deve ser maior que R$ ${item.current_price.toFixed(2)}.`,
      }))
      return
    }

    send('PLACE_BID', { item_id: item.item_id, amount })
    setBidAmounts((prev) => ({ ...prev, [item.item_id]: '' }))
    setBidSuccess((prev) => ({ ...prev, [item.item_id]: 'Lance enviado!' }))
    setTimeout(() => setBidSuccess((prev) => ({ ...prev, [item.item_id]: '' })), 3000)
  }

  const displayedItems = activeTab === 'active' ? activeItems : closedItems

  return (
    <div style={styles.layout}>
      {/* Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.sideHeader}>
          <span style={styles.logo}>🔨 LeilãoNet</span>
          <span style={styles.roleTag}>Comprador</span>
        </div>

        <div style={styles.userInfo}>
          <span style={styles.userName}>{currentUser?.name}</span>
          <span style={{ ...styles.connDot, backgroundColor: connected ? '#22c55e' : '#ef4444' }} />
        </div>

        {/* Meus lances vencendo */}
        <div style={styles.statsBox}>
          <p style={styles.statsTitle}>Meus lances</p>
          <p style={styles.statValue}>
            {items.filter((i) => i.current_winner === currentUser?.name && i.is_active).length}
          </p>
          <p style={styles.statsSubtitle}>leilões liderando</p>
          <p style={styles.statValue} >
            {items.filter((i) => i.current_winner === currentUser?.name && !i.is_active).length}
          </p>
          <p style={styles.statsSubtitle}>leilões ganhos</p>
        </div>

        <nav style={styles.nav}>
          <button onClick={() => setActiveTab('active')} style={{ ...styles.navBtn, ...(activeTab === 'active' ? styles.navBtnActive : {}) }}>
            🏷 Ativos ({activeItems.length})
          </button>
          <button onClick={() => setActiveTab('closed')} style={{ ...styles.navBtn, ...(activeTab === 'closed' ? styles.navBtnActive : {}) }}>
            ✅ Encerrados ({closedItems.length})
          </button>
        </nav>

        <button onClick={logout} style={styles.logoutBtn}>Sair</button>
      </aside>

      {/* Main */}
      <main style={styles.main}>
        {/* Painel de monitoramento ao vivo */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>
            📡 Painel em Tempo Real
            <span style={styles.liveBadge}>● AO VIVO</span>
          </h2>
          <LogPanel logs={logs} />
        </section>

        {/* Lista de itens */}
        <section style={styles.section}>
          <h2 style={styles.sectionTitle}>
            {activeTab === 'active' ? '🏷 Leilões Ativos' : '✅ Leilões Encerrados'}
          </h2>

          {displayedItems.length === 0 ? (
            <p style={styles.empty}>
              {activeTab === 'active'
                ? 'Nenhum leilão ativo no momento. Aguarde o administrador cadastrar itens.'
                : 'Nenhum leilão encerrado ainda.'}
            </p>
          ) : (
            <div style={styles.grid}>
              {displayedItems.map((item) => {
                const isWinning = item.current_winner === currentUser?.name
                return (
                  <div
                    key={item.item_id}
                    style={{
                      ...styles.card,
                      borderLeft: isWinning
                        ? '4px solid #22c55e'
                        : item.is_active
                        ? '4px solid #2563eb'
                        : '4px solid #9ca3af',
                    }}
                  >
                    {/* Cabeçalho */}
                    <div style={styles.cardHeader}>
                      <span style={styles.cardId}>#{item.item_id}</span>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {isWinning && (
                          <span style={styles.winningBadge}>🏆 Vencendo</span>
                        )}
                        <span style={{ ...styles.statusBadge, backgroundColor: item.is_active ? '#dbeafe' : '#f3f4f6', color: item.is_active ? '#1d4ed8' : '#6b7280' }}>
                          {item.is_active ? 'Ativo' : 'Encerrado'}
                        </span>
                      </div>
                    </div>

                    <h3 style={styles.cardName}>{item.name}</h3>
                    {item.description && <p style={styles.cardDesc}>{item.description}</p>}

                    {/* Preços */}
                    <div style={styles.priceRow}>
                      <div>
                        <span style={styles.priceLabel}>Lance inicial</span>
                        <span style={styles.priceValue}>R$ {item.starting_price.toFixed(2)}</span>
                      </div>
                      <div>
                        <span style={styles.priceLabel}>Lance atual</span>
                        <span style={{ ...styles.priceValue, fontSize: 20, color: '#2563eb' }}>
                          R$ {item.current_price.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {item.current_winner && (
                      <p style={styles.winnerInfo}>
                        Líder: <strong>{item.current_winner}</strong>
                      </p>
                    )}

                    {/* Formulário de lance */}
                    {item.is_active && (
                      <div style={styles.bidArea}>
                        <div style={styles.bidRow}>
                          <input
                            style={styles.bidInput}
                            type="number"
                            placeholder={`Mín: R$ ${(item.current_price + 0.01).toFixed(2)}`}
                            min={item.current_price + 0.01}
                            step="0.01"
                            value={bidAmounts[item.item_id] ?? ''}
                            onChange={(e) =>
                              setBidAmounts((prev) => ({ ...prev, [item.item_id]: e.target.value }))
                            }
                            onKeyDown={(e) => e.key === 'Enter' && handleBid(item)}
                          />
                          <button onClick={() => handleBid(item)} style={styles.bidBtn}>
                            Dar Lance
                          </button>
                        </div>
                        {bidErrors[item.item_id] && (
                          <p style={styles.bidError}>{bidErrors[item.item_id]}</p>
                        )}
                        {bidSuccess[item.item_id] && (
                          <p style={styles.bidSuccess}>{bidSuccess[item.item_id]}</p>
                        )}
                      </div>
                    )}

                    {/* Resultado final */}
                    {!item.is_active && (
                      <div style={styles.closedResult}>
                        {item.current_winner
                          ? `🏆 Vencedor: ${item.current_winner} — R$ ${item.current_price.toFixed(2)}`
                          : 'Encerrado sem lances.'}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  layout: { display: 'flex', minHeight: '100vh', backgroundColor: '#f9fafb' },
  sidebar: { width: 220, backgroundColor: '#1e293b', color: '#fff', display: 'flex', flexDirection: 'column', padding: 20, gap: 12, flexShrink: 0 },
  sideHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logo: { fontWeight: 700, fontSize: 18 },
  roleTag: { backgroundColor: '#3b82f6', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 11, fontWeight: 700 },
  userInfo: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#334155', borderRadius: 8, padding: '8px 12px' },
  userName: { fontSize: 14, fontWeight: 600 },
  connDot: { width: 10, height: 10, borderRadius: '50%', flexShrink: 0 },
  statsBox: { backgroundColor: '#0f172a', borderRadius: 8, padding: 12 },
  statsTitle: { fontSize: 11, color: '#64748b', margin: '0 0 4px', textTransform: 'uppercase', letterSpacing: 1 },
  statValue: { fontSize: 28, fontWeight: 700, color: '#38bdf8', margin: '0 0 2px' },
  statsSubtitle: { fontSize: 12, color: '#94a3b8', margin: '0 0 8px' },
  nav: { display: 'flex', flexDirection: 'column', gap: 6, flex: 1 },
  navBtn: { background: 'none', border: 'none', color: '#94a3b8', textAlign: 'left', padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
  navBtnActive: { backgroundColor: '#334155', color: '#f1f5f9' },
  logoutBtn: { background: 'none', border: '1px solid #475569', color: '#94a3b8', borderRadius: 6, padding: '8px', cursor: 'pointer', fontSize: 13 },
  main: { flex: 1, padding: 28, overflowY: 'auto' },
  section: { marginBottom: 32, maxWidth: 1100 },
  sectionTitle: { fontSize: 18, fontWeight: 700, color: '#1f2937', marginBottom: 14, borderBottom: '2px solid #e5e7eb', paddingBottom: 8, display: 'flex', alignItems: 'center', gap: 12 },
  liveBadge: { fontSize: 12, color: '#dc2626', fontWeight: 700, animation: 'none' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 },
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 18, boxShadow: '0 1px 6px rgba(0,0,0,0.08)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8, flexWrap: 'wrap', gap: 4 },
  cardId: { fontSize: 11, color: '#9ca3af', fontFamily: 'monospace' },
  winningBadge: { fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 20, backgroundColor: '#dcfce7', color: '#15803d' },
  statusBadge: { fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20 },
  cardName: { fontSize: 16, fontWeight: 700, color: '#1f2937', margin: '0 0 6px' },
  cardDesc: { fontSize: 13, color: '#6b7280', marginBottom: 12 },
  priceRow: { display: 'flex', gap: 20, marginBottom: 10 },
  priceLabel: { display: 'block', fontSize: 11, color: '#9ca3af' },
  priceValue: { display: 'block', fontSize: 15, fontWeight: 600, color: '#1f2937' },
  winnerInfo: { fontSize: 13, color: '#374151', marginBottom: 10 },
  bidArea: { borderTop: '1px solid #f3f4f6', paddingTop: 12, marginTop: 4 },
  bidRow: { display: 'flex', gap: 8 },
  bidInput: { flex: 1, padding: '8px 10px', border: '1.5px solid #d1d5db', borderRadius: 6, fontSize: 13, outline: 'none', minWidth: 0 },
  bidBtn: { padding: '8px 14px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' },
  bidError: { color: '#dc2626', fontSize: 12, marginTop: 4 },
  bidSuccess: { color: '#16a34a', fontSize: 12, marginTop: 4 },
  closedResult: { marginTop: 10, padding: '8px 12px', backgroundColor: '#f9fafb', borderRadius: 6, fontSize: 13, color: '#374151', fontWeight: 600 },
  empty: { color: '#9ca3af', fontSize: 14 },
}