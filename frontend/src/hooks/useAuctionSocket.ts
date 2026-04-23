import { useEffect, useRef, useCallback, useState } from 'react'
import type { ServerMessage, ClientMessageType } from '../types/Index'


const WS_URL = 'ws://localhost:6789'

export type MessageHandler = (msg: ServerMessage) => void

interface UseAuctionSocketReturn {
  connected: boolean
  send: (type: ClientMessageType, payload?: Record<string, unknown>) => void
  onMessage: (handler: MessageHandler) => () => void
}

/**
 * Hook que gerencia a conexão WebSocket com o bridge do servidor de leilões.
 * Reconecta automaticamente caso a conexão caia.
 */
export function useAuctionSocket(): UseAuctionSocketReturn {
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Set<MessageHandler>>(new Set())
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // Tenta reconectar após 3s
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      ws.close()
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data as string)
        handlersRef.current.forEach((h) => h(msg))
      } catch {
        console.warn('[WS] Mensagem inválida:', event.data)
      }
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  /**
   * Envia uma mensagem ao servidor via WebSocket.
   */
  const send = useCallback((type: ClientMessageType, payload: Record<string, unknown> = {}) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Tentativa de envio com socket fechado')
      return
    }
    ws.send(JSON.stringify({ type, payload }))
  }, [])

  /**
   * Registra um handler para mensagens do servidor.
   * Retorna uma função de cleanup para desregistrar.
   */
  const onMessage = useCallback((handler: MessageHandler) => {
    handlersRef.current.add(handler)
    return () => {
      handlersRef.current.delete(handler)
    }
  }, [])

  return { connected, send, onMessage }
}