import React, { useState } from 'react'
import { useAuction } from '../context/Auctioncontext'
import logoUrl from '../assets/dayfox-logo.webp'

export default function LoginPage() {
  const { register, connected } = useAuction()
  const [name, setName] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) { setError('Informe seu nome para continuar.'); return }
    if (trimmed.length < 2) { setError('Nome deve ter ao menos 2 caracteres.'); return }
    setError('')
    register(trimmed, isAdmin)
  }

  return (
    <div style={s.page}>
      {/* Decoração de fundo */}
      <div style={s.bgCircle1} />
      <div style={s.bgCircle2} />

      <div style={s.card}>
        {/* Logo */}
        <div style={s.logoWrap}>
          <img src={logoUrl} alt="DayFox" style={s.logoImg} />
        </div>

        {/* Status de conexão */}
        <div style={{ ...s.connBadge, background: connected ? '#dcfce7' : '#fee2e2', color: connected ? '#15803d' : '#991b1b' }}>
          <span style={{ ...s.connDot, background: connected ? '#22c55e' : '#ef4444' }} />
          {connected ? 'Servidor conectado' : 'Aguardando conexão…'}
        </div>

        <p style={s.welcome}>Bem-vindo ao maior leilão online da raposarada! 🦊</p>

        <form onSubmit={handleSubmit} style={s.form}>
          <div style={s.field}>
            <label style={s.label}>Seu nome</label>
            <input
              style={s.input}
              type="text"
              placeholder="Ex: João Raposão"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!connected}
              maxLength={40}
            />
          </div>

          <label style={s.checkRow}>
            <input
              type="checkbox"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              disabled={!connected}
              style={s.checkbox}
            />
            <span style={s.checkLabel}>Entrar como Administrador</span>
          </label>

          {error && <p style={s.error}>{error}</p>}

          <button
            type="submit"
            disabled={!connected}
            style={{ ...s.btn, opacity: connected ? 1 : 0.5, cursor: connected ? 'pointer' : 'not-allowed' }}
          >
            Entrar no Leilão
          </button>
        </form>

        <p style={s.hint}>Admins criam itens e encerram leilões · Compradores dão lances</p>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #FFF8F0 0%, #FFE8D0 50%, #FFF0E0 100%)',
    padding: 16,
    position: 'relative',
    overflow: 'hidden',
    fontFamily: "'Nunito', sans-serif",
  },
  bgCircle1: {
    position: 'absolute', top: -120, right: -120,
    width: 400, height: 400, borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(232,101,26,0.12) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  bgCircle2: {
    position: 'absolute', bottom: -80, left: -80,
    width: 300, height: 300, borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(245,166,35,0.15) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  card: {
    background: '#fff',
    borderRadius: 24,
    padding: '36px 40px',
    width: '100%',
    maxWidth: 440,
    boxShadow: '0 8px 40px rgba(196,66,15,0.12)',
    textAlign: 'center',
    position: 'relative',
    zIndex: 1,
  },
  logoWrap: { display: 'flex', justifyContent: 'center', marginBottom: 8 },
  logoImg: { width: 160, height: 'auto', objectFit: 'contain' },
  connBadge: {
    display: 'inline-flex', alignItems: 'center', gap: 7,
    padding: '5px 14px', borderRadius: 20,
    fontSize: 12, fontWeight: 700, marginBottom: 16,
  },
  connDot: { width: 8, height: 8, borderRadius: '50%', flexShrink: 0 },
  welcome: { fontSize: 14, color: '#8B5E3C', marginBottom: 24, lineHeight: 1.5 },
  form: { textAlign: 'left' },
  field: { marginBottom: 16 },
  label: { display: 'block', fontWeight: 700, fontSize: 13, color: '#1C1107', marginBottom: 6 },
  input: {
    width: '100%', padding: '11px 14px',
    border: '2px solid #F0D9C8', borderRadius: 10,
    fontSize: 15, outline: 'none', fontFamily: "'Nunito', sans-serif",
    transition: 'border-color 0.2s',
    color: '#1C1107',
  },
  checkRow: {
    display: 'flex', alignItems: 'center', gap: 10,
    marginBottom: 18, cursor: 'pointer',
  },
  checkbox: { width: 17, height: 17, cursor: 'pointer', accentColor: '#E8651A' },
  checkLabel: { fontSize: 14, color: '#1C1107', fontWeight: 600 },
  error: { color: '#C0392B', fontSize: 13, marginBottom: 10, fontWeight: 600 },
  btn: {
    width: '100%', padding: '13px',
    background: 'linear-gradient(135deg, #E8651A, #C4420F)',
    color: '#fff', border: 'none', borderRadius: 10,
    fontSize: 16, fontWeight: 800, fontFamily: "'Nunito', sans-serif",
    boxShadow: '0 4px 16px rgba(196,66,15,0.30)',
    transition: 'transform 0.1s',
  },
  hint: { marginTop: 20, fontSize: 12, color: '#8B5E3C', lineHeight: 1.7 },
}