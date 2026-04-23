import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { useAuctionSocket } from '../hooks/useAuctionSocket'
import type {
  CurrentUser,
  AuctionItem,
  LogEntry,
  ServerMessage,
  WelcomePayload,
  ItemAddedPayload,
  BidAcceptedPayload,
  AuctionClosedPayload,
  ItemsListPayload,
  ClientMessageType,
} from '../types/Index'

// ─── Contexto ─────────────────────────────────────────────────────

interface AuctionContextValue {
  // conexão
  connected: boolean
  // usuário
  currentUser: CurrentUser | null
  register: (name: string, isAdmin: boolean) => void
  logout: () => void
  // leilão
  items: AuctionItem[]
  logs: LogEntry[]
  // ações
  send: (type: ClientMessageType, payload?: Record<string, unknown>) => void
}

const AuctionContext = createContext<AuctionContextValue | null>(null)

// ─── Provider ─────────────────────────────────────────────────────

let logIdCounter = 0

export function AuctionProvider({ children }: { children: React.ReactNode }) {
  const { connected, send, onMessage } = useAuctionSocket()

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(() => {
    const saved = sessionStorage.getItem('auction_user')
    return saved ? (JSON.parse(saved) as CurrentUser) : null
  })

  const [items, setItems] = useState<AuctionItem[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const registeredRef = useRef(false)

  const addLog = useCallback((type: LogEntry['type'], message: string) => {
    const entry: LogEntry = {
      id: ++logIdCounter,
      type,
      message,
      timestamp: new Date().toLocaleTimeString('pt-BR'),
    }
    setLogs((prev) => [entry, ...prev].slice(0, 100)) // máx 100 entradas
  }, [])

  // ── Handlers de mensagens do servidor ──────────────────────────

  useEffect(() => {
    const unsub = onMessage((msg: ServerMessage) => {
      const p = msg.payload

      switch (msg.type) {
        case 'WELCOME': {
          const payload = p as unknown as WelcomePayload
          const user: CurrentUser = { name: payload.name, isAdmin: payload.is_admin }
          setCurrentUser(user)
          sessionStorage.setItem('auction_user', JSON.stringify(user))
          registeredRef.current = true
          addLog('INFO', payload.message)
          // Pede lista de itens logo após registrar
          send('LIST_ITEMS')
          break
        }

        case 'ITEM_ADDED': {
          const payload = p as unknown as ItemAddedPayload
          setItems((prev) => {
            const exists = prev.find((i) => i.item_id === payload.item.item_id)
            if (exists) return prev
            return [...prev, payload.item]
          })
          addLog('ITEM_ADDED', payload.message)
          break
        }

        case 'BID_ACCEPTED': {
          const payload = p as unknown as BidAcceptedPayload
          setItems((prev) =>
            prev.map((item) =>
              item.item_id === payload.bid.item_id
                ? {
                    ...item,
                    current_price: payload.bid.amount,
                    current_winner: payload.bid.bidder,
                  }
                : item
            )
          )
          addLog('BID_ACCEPTED', payload.message)
          break
        }

        case 'BID_REJECTED': {
          const message = (p as { message: string }).message
          addLog('BID_REJECTED', `Lance rejeitado: ${message}`)
          break
        }

        case 'AUCTION_CLOSED': {
          const payload = p as unknown as AuctionClosedPayload
          setItems((prev) =>
            prev.map((item) =>
              item.item_id === payload.item.item_id ? { ...item, is_active: false } : item
            )
          )
          addLog('AUCTION_CLOSED', payload.message)
          break
        }

        case 'ITEMS_LIST': {
          const payload = p as unknown as ItemsListPayload
          setItems(payload.items)
          break
        }

        case 'ERROR': {
          const message = (p as { message: string }).message
          addLog('ERROR', `Erro: ${message}`)
          break
        }

        default:
          break
      }
    })
    return unsub
  }, [onMessage, send, addLog])

  // ── Re-registra automaticamente ao reconectar ───────────────────

  useEffect(() => {
    if (connected && currentUser && !registeredRef.current) {
      send('REGISTER', { name: currentUser.name, is_admin: currentUser.isAdmin })
    }
    if (!connected) {
      registeredRef.current = false
    }
  }, [connected, currentUser, send])

  // ── Ações públicas ──────────────────────────────────────────────

  const register = useCallback(
    (name: string, isAdmin: boolean) => {
      send('REGISTER', { name, is_admin: isAdmin })
    },
    [send]
  )

  const logout = useCallback(() => {
    setCurrentUser(null)
    setItems([])
    setLogs([])
    registeredRef.current = false
    sessionStorage.removeItem('auction_user')
  }, [])

  return (
    <AuctionContext.Provider value={{ connected, currentUser, register, logout, items, logs, send }}>
      {children}
    </AuctionContext.Provider>
  )
}

// ─── Hook de acesso ────────────────────────────────────────────────

export function useAuction(): AuctionContextValue {
  const ctx = useContext(AuctionContext)
  if (!ctx) throw new Error('useAuction deve ser usado dentro de AuctionProvider')
  return ctx
}