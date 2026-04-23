// ─── Mensagens enviadas ao servidor ──────────────────────────────

export type ClientMessageType =
  | 'REGISTER'
  | 'ADD_ITEM'
  | 'PLACE_BID'
  | 'CLOSE_AUCTION'
  | 'LIST_ITEMS'
  | 'PING'

// ─── Mensagens recebidas do servidor ─────────────────────────────

export type ServerMessageType =
  | 'WELCOME'
  | 'ITEM_ADDED'
  | 'BID_ACCEPTED'
  | 'BID_REJECTED'
  | 'AUCTION_CLOSED'
  | 'ITEMS_LIST'
  | 'ERROR'
  | 'PONG'
  | 'NOTIFICATION'

// ─── Estruturas de dados ──────────────────────────────────────────

export interface AuctionItem {
  item_id: string
  name: string
  description: string
  starting_price: number
  current_price: number
  current_winner: string | null
  is_active: boolean
}

export interface Bid {
  item_id: string
  bidder: string
  amount: number
  timestamp: string
}

// ─── Envelope de mensagem do servidor ────────────────────────────

export interface ServerMessage {
  type: ServerMessageType
  payload: Record<string, unknown>
}

// ─── Payloads específicos ─────────────────────────────────────────

export interface WelcomePayload {
  name: string
  is_admin: boolean
  message: string
}

export interface ItemAddedPayload {
  item: AuctionItem
  message: string
}

export interface BidAcceptedPayload {
  bid: Bid
  message: string
}

export interface BidRejectedPayload {
  message: string
}

export interface AuctionClosedPayload {
  item: AuctionItem
  winner: string
  final_price: number
  message: string
}

export interface ItemsListPayload {
  items: AuctionItem[]
}

export interface ErrorPayload {
  message: string
}

// ─── Estado do usuário logado ──────────────────────────────────────

export interface CurrentUser {
  name: string
  isAdmin: boolean
}

// ─── Entradas de log do painel ────────────────────────────────────

export interface LogEntry {
  id: number
  type: ServerMessageType | 'INFO'
  message: string
  timestamp: string
}