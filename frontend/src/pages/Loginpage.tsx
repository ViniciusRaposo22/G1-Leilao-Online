import React, { useState } from 'react'
import { useAuction } from '../context/Auctioncontext'

export default function LoginPage() {
  const { register, connected } = useAuction()
  const [name, setName] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setError('Informe seu nome para continuar.')
      return
    }
    if (trimmed.length < 2) {
      setError('Nome deve ter ao menos 2 caracteres.')
      return
    }
    setError('')
    register(trimmed, isAdmin)
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>🔨 LeilãoNet</h1>
        <p style={styles.subtitle}>Plataforma de Leilões Eletrônicos</p>

        <div style={{ ...styles.badge, backgroundColor: connected ? '#d1fae5' : '#fee2e2', color: connected ? '#065f46' : '#991b1b' }}>
          {connected ? '● Conectado ao servidor' : '○ Aguardando conexão…'}
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.field}>
            <label style={styles.label}>Seu nome</label>
            <input
              style={styles.input}
              type="text"
              placeholder="Ex: João Silva"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!connected}
              maxLength={40}
            />
          </div>

          <div style={styles.checkRow}>
            <input
              type="checkbox"
              id="admin"
              checked={isAdmin}
              onChange={(e) => setIsAdmin(e.target.checked)}
              disabled={!connected}
              style={{ width: 16, height: 16, cursor: 'pointer' }}
            />
            <label htmlFor="admin" style={styles.checkLabel}>
              Entrar como Administrador
            </label>
          </div>

          {error && <p style={styles.error}>{error}</p>}

          <button
            type="submit"
            disabled={!connected}
            style={{ ...styles.button, opacity: connected ? 1 : 0.5, cursor: connected ? 'pointer' : 'not-allowed' }}
          >
            Entrar no Leilão
          </button>
        </form>

        <p style={styles.hint}>
          Administradores podem criar itens e encerrar leilões.<br />
          Usuários comuns visualizam e dão lances.
        </p>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f3f4f6',
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: '40px 36px',
    width: '100%',
    maxWidth: 420,
    boxShadow: '0 4px 24px rgba(0,0,0,0.10)',
    textAlign: 'center',
  },
  title: { fontSize: 32, fontWeight: 700, margin: 0, color: '#1f2937' },
  subtitle: { color: '#6b7280', marginTop: 6, marginBottom: 20, fontSize: 15 },
  badge: {
    display: 'inline-block',
    padding: '4px 14px',
    borderRadius: 20,
    fontSize: 13,
    fontWeight: 600,
    marginBottom: 24,
  },
  form: { textAlign: 'left' },
  field: { marginBottom: 16 },
  label: { display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14, color: '#374151' },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1.5px solid #d1d5db',
    borderRadius: 8,
    fontSize: 15,
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s',
  },
  checkRow: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 },
  checkLabel: { fontSize: 14, color: '#374151', cursor: 'pointer' },
  error: { color: '#dc2626', fontSize: 13, marginBottom: 10, marginTop: -6 },
  button: {
    width: '100%',
    padding: '12px',
    backgroundColor: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    fontSize: 16,
    fontWeight: 600,
    transition: 'background 0.15s',
  },
  hint: { marginTop: 20, fontSize: 13, color: '#9ca3af', lineHeight: 1.6 },
}