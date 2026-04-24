import React, { useState } from 'react'
import { useAuction } from '../context/Auctioncontext'
import { LogPanel } from './Adminpage'
import type { AuctionItem } from '../types/Index'
import logoUrl from '../assets/dayfox-logo.webp'

export default function BuyerPage() {
  const { items, send, currentUser, logout, connected, logs } = useAuction()
  const [bidAmounts, setBidAmounts] = useState<Record<string, string>>({})
  const [bidErrors, setBidErrors] = useState<Record<string, string>>({})
  const [bidSuccess, setBidSuccess] = useState<Record<string, string>>({})
  const [activeTab, setActiveTab] = useState<'active' | 'closed'>('active')

  const activeItems = items.filter((i) => i.is_active)
  const closedItems = items.filter((i) => !i.is_active)
  const winning = items.filter((i) => i.current_winner === currentUser?.name && i.is_active)
  const won = items.filter((i) => i.current_winner === currentUser?.name && !i.is_active)

  const handleBid = (item: AuctionItem) => {
    const raw = bidAmounts[item.item_id] ?? ''
    const amount = parseFloat(raw)
    setBidErrors((p) => ({ ...p, [item.item_id]: '' }))
    setBidSuccess((p) => ({ ...p, [item.item_id]: '' }))
    if (!raw || isNaN(amount) || amount <= 0) {
      setBidErrors((p) => ({ ...p, [item.item_id]: 'Informe um valor válido.' })); return
    }
    if (amount <= item.current_price) {
      setBidErrors((p) => ({ ...p, [item.item_id]: `Lance deve ser maior que R$ ${item.current_price.toFixed(2)}.` })); return
    }
    send('PLACE_BID', { item_id: item.item_id, amount })
    setBidAmounts((p) => ({ ...p, [item.item_id]: '' }))
    setBidSuccess((p) => ({ ...p, [item.item_id]: 'Lance enviado!' }))
    setTimeout(() => setBidSuccess((p) => ({ ...p, [item.item_id]: '' })), 3000)
  }

  const displayed = activeTab === 'active' ? activeItems : closedItems

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
            <div style={s.userRole}>Comprador</div>
          </div>
          <div style={{ ...s.connDot, background: connected ? '#22c55e' : '#ef4444' }} />
        </div>

        {/* Stats pessoais */}
        <div style={s.statsGrid}>
          <div style={s.statBox}>
            <span style={s.statNum}>{winning.length}</span>
            <span style={s.statLabel}>Liderando</span>
          </div>
          <div style={s.statBox}>
            <span style={s.statNum}>{won.length}</span>
            <span style={s.statLabel}>Ganhos</span>
          </div>
        </div>

        <nav style={s.nav}>
          <button onClick={() => setActiveTab('active')}
            style={{ ...s.navBtn, ...(activeTab === 'active' ? s.navBtnActive : {}) }}>
            🏷 Ativos ({activeItems.length})
          </button>
          <button onClick={() => setActiveTab('closed')}
            style={{ ...s.navBtn, ...(activeTab === 'closed' ? s.navBtnActive : {}) }}>
            Encerrados ({closedItems.length})
          </button>
        </nav>

        <div style={{ flex: 1 }} />
        <button onClick={logout} style={s.logoutBtn}>Sair</button>
      </aside>

      {/* ── Main ── */}
      <main style={s.main}>
        {/* Painel ao vivo */}
        <section style={s.section}>
          <h2 style={s.sectionTitle}>
            Painel em Tempo Real
            <span style={s.liveBadge}>● AO VIVO</span>
          </h2>
          <LogPanel logs={logs} />
        </section>

        {/* Itens */}
        <section style={s.section}>
          <h2 style={s.sectionTitle}>
            {activeTab === 'active' ? 'Leilões Ativos' : 'Leilões Encerrados'}
          </h2>
          {displayed.length === 0 ? (
            <p style={s.empty}>
              {activeTab === 'active'
                ? 'Nenhum leilão ativo. Aguarde o administrador cadastrar itens.'
                : 'Nenhum leilão encerrado ainda.'}
            </p>
          ) : (
            <div style={s.grid}>
              {displayed.map((item) => {
                const isWinning = item.current_winner === currentUser?.name
                return (
                  <div key={item.item_id} style={{
                    ...s.card,
                    borderTop: isWinning ? '4px solid #22c55e' : item.is_active ? '4px solid #E8651A' : '4px solid #d1d5db',
                  }}>
                    <div style={s.cardHeader}>
                      <span style={s.cardId}>#{item.item_id}</span>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {isWinning && <span style={s.winBadge}>🏆 Vencendo</span>}
                        <span style={{ ...s.badge, background: item.is_active ? '#fff3e0' : '#f3f4f6', color: item.is_active ? '#C4420F' : '#6b7280' }}>
                          {item.is_active ? '● Ativo' : '○ Encerrado'}
                        </span>
                      </div>
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
                        <span style={{ ...s.priceVal, color: '#E8651A', fontSize: 20, fontWeight: 800 }}>
                          R$ {item.current_price.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {item.current_winner && (
                      <p style={s.winner}>Líder: <strong>{item.current_winner}</strong></p>
                    )}

                    {item.is_active && (
                      <div style={s.bidArea}>
                        <div style={s.bidRow}>
                          <input
                            style={s.bidInput}
                            type="number"
                            placeholder={`Mín: R$ ${(item.current_price + 0.01).toFixed(2)}`}
                            min={item.current_price + 0.01}
                            step="0.01"
                            value={bidAmounts[item.item_id] ?? ''}
                            onChange={(e) => setBidAmounts((p) => ({ ...p, [item.item_id]: e.target.value }))}
                            onKeyDown={(e) => e.key === 'Enter' && handleBid(item)}
                          />
                          <button onClick={() => handleBid(item)} style={s.bidBtn}>
                            Dar Lance
                          </button>
                        </div>
                        {bidErrors[item.item_id] && <p style={s.bidError}>{bidErrors[item.item_id]}</p>}
                        {bidSuccess[item.item_id] && <p style={s.bidOk}>{bidSuccess[item.item_id]}</p>}
                      </div>
                    )}

                    {!item.is_active && (
                      <div style={s.closedResult}>
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

const s: Record<string, React.CSSProperties> = {
  layout: { display: 'flex', minHeight: '100vh', background: '#FFF8F0', fontFamily: "'Nunito', sans-serif" },

  sidebar: { width: 230, background: '#52290a', color: '#fff', display: 'flex', flexDirection: 'column', padding: '20px 16px', gap: 16, flexShrink: 0 },
  sideTop: { display: 'flex', justifyContent: 'center', paddingBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.08)' },
  sideLogoImg: { width: 130, height: 'auto', objectFit: 'contain' },
  userCard: { display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(255,255,255,0.07)', borderRadius: 10, padding: '10px 12px' },
  userAvatar: { width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg,#E8651A,#F5A623)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16, flexShrink: 0 },
  userName: { fontSize: 14, fontWeight: 700, lineHeight: 1.2 },
  userRole: { fontSize: 11, color: '#60a5fa', fontWeight: 600 },
  connDot: { width: 9, height: 9, borderRadius: '50%', marginLeft: 'auto', flexShrink: 0 },
  statsGrid: { display: 'flex', gap: 8 },
  statBox: { flex: 1, background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: '10px 8px', textAlign: 'center' },
  statNum: { display: 'block', fontSize: 22, fontWeight: 800, color: '#F5A623' },
  statLabel: { fontSize: 11, color: '#c4a882' },
  nav: { display: 'flex', flexDirection: 'column', gap: 6 },
  navBtn: { background: 'none', border: 'none', color: '#c4a882', textAlign: 'left', padding: '9px 12px', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontFamily: "'Nunito', sans-serif", fontWeight: 600 },
  navBtnActive: { background: 'rgba(232,101,26,0.20)', color: '#F5A623' },
  logoutBtn: { background: 'none', border: '1px solid rgba(255,255,255,0.15)', color: '#c4a882', borderRadius: 8, padding: '9px', cursor: 'pointer', fontSize: 13, fontFamily: "'Nunito', sans-serif", fontWeight: 600 },

  main: { flex: 1, padding: '28px 32px', overflowY: 'auto' },
  section: { marginBottom: 36, maxWidth: 1100 },
  sectionTitle: { fontSize: 18, fontWeight: 800, color: '#1C1107', marginBottom: 16, paddingBottom: 10, borderBottom: '2px solid #F0D9C8', display: 'flex', alignItems: 'center', gap: 12 },
  liveBadge: { fontSize: 12, color: '#C0392B', fontWeight: 800 },

  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))', gap: 16 },
  card: { background: '#fff', borderRadius: 12, padding: 18, boxShadow: '0 2px 10px rgba(196,66,15,0.07)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10, gap: 6, flexWrap: 'wrap' },
  cardId: { fontSize: 11, color: '#8B5E3C', fontFamily: 'monospace', fontWeight: 700 },
  badge: { fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20 },
  winBadge: { fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20, background: '#dcfce7', color: '#15803d' },
  cardName: { fontSize: 16, fontWeight: 800, color: '#1C1107', marginBottom: 4 },
  cardDesc: { fontSize: 13, color: '#8B5E3C', marginBottom: 12 },
  priceRow: { display: 'flex', gap: 20, marginBottom: 10 },
  priceLabel: { display: 'block', fontSize: 11, color: '#8B5E3C', marginBottom: 2 },
  priceVal: { display: 'block', fontSize: 15, fontWeight: 700, color: '#1C1107' },
  winner: { fontSize: 13, color: '#1C1107', marginBottom: 10 },
  bidArea: { borderTop: '1px solid #F0D9C8', paddingTop: 12, marginTop: 6 },
  bidRow: { display: 'flex', gap: 8 },
  bidInput: { flex: 1, padding: '9px 10px', border: '2px solid #F0D9C8', borderRadius: 7, fontSize: 13, outline: 'none', minWidth: 0, fontFamily: "'Nunito', sans-serif", color: '#1C1107' },
  bidBtn: { padding: '9px 14px', background: 'linear-gradient(135deg,#E8651A,#C4420F)', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 800, cursor: 'pointer', whiteSpace: 'nowrap', fontFamily: "'Nunito', sans-serif", boxShadow: '0 2px 8px rgba(196,66,15,0.25)' },
  bidError: { color: '#C0392B', fontSize: 12, marginTop: 5, fontWeight: 600 },
  bidOk: { color: '#2D9C4A', fontSize: 12, marginTop: 5, fontWeight: 600 },
  closedResult: { marginTop: 10, padding: '9px 12px', background: '#FFF8F0', borderRadius: 7, fontSize: 13, color: '#1C1107', fontWeight: 700 },
  empty: { color: '#8B5E3C', fontSize: 14, opacity: 0.7 },
}