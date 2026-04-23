# Sistema de Leilões Eletrônicos — Backend

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/TS)                       │
│                   ws://localhost:6789 (WebSocket)                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     ws_bridge.py (porta 6789)                    │
│           Bridge WebSocket ↔ TCP (asyncio + websockets)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ TCP
┌──────────────────────────▼──────────────────────────────────────┐
│                      server.py (porta 5555)                      │
│              Servidor TCP Multithread (socket + threading)        │
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ ClientHandler│   │ ClientHandler│   │   ClientRegistry      │ │
│  │   Thread 1   │   │   Thread 2   │   │ (broadcast + lookup)  │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              AuctionManager (estado compartilhado)          │  │
│  │          items: Dict | bids: List | RLock thread-safe       │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Arquivos

| Arquivo             | Responsabilidade                                       |
|---------------------|--------------------------------------------------------|
| `protocol.py`       | Tipos de mensagem, serialização/desserialização JSON   |
| `auction_manager.py`| Estado dos leilões (itens, lances) — thread-safe       |
| `server.py`         | Servidor TCP + ClientHandler threads + ClientRegistry  |
| `ws_bridge.py`      | Bridge WebSocket→TCP para o frontend React             |
| `client_cli.py`     | Cliente CLI para testes sem o frontend                 |

## Instalação

```bash
pip install websockets
```

## Como executar

### 1. Servidor TCP
```bash
python server.py
# ou com host/porta customizados:
python server.py 0.0.0.0 5555
```

### 2. Bridge WebSocket (para o frontend React)
```bash
python ws_bridge.py
# ou:
python ws_bridge.py 6789 127.0.0.1 5555
```

### 3. Cliente CLI (testes)
```bash
python client_cli.py
```

## Protocolo de Mensagens (JSON sobre TCP / WebSocket)

### Cliente → Servidor

```json
// Registrar participante
{"type": "REGISTER", "payload": {"name": "João", "is_admin": false}}

// Cadastrar item (admin)
{"type": "ADD_ITEM", "payload": {"name": "Violão", "description": "Giannini", "starting_price": 500.0}}

// Dar lance
{"type": "PLACE_BID", "payload": {"item_id": "A1B2C3D4", "amount": 750.0}}

// Encerrar leilão (admin)
{"type": "CLOSE_AUCTION", "payload": {"item_id": "A1B2C3D4"}}

// Listar itens
{"type": "LIST_ITEMS", "payload": {}}
```

### Servidor → Clientes (broadcast)

```json
// Lance aceito (broadcast)
{"type": "BID_ACCEPTED", "payload": {"bid": {...}, "message": "..."}}

// Leilão encerrado (broadcast)
{"type": "AUCTION_CLOSED", "payload": {"item": {...}, "winner": "João", "final_price": 750.0}}

// Novo item (broadcast)
{"type": "ITEM_ADDED", "payload": {"item": {...}, "message": "..."}}
```

## Decisões de Design

- **Thread por cliente**: modelo simples e didático, adequado para a escala do sistema de leilões.
- **RLock no AuctionManager**: garante que lances concorrentes não corrompam o estado.
- **Broadcast com lock**: evita race conditions ao iterar sobre clientes conectados.
- **Bridge WS↔TCP**: separa responsabilidades — o servidor TCP é puro e testável via CLI; o bridge adiciona a camada WebSocket apenas para o frontend.
- **Delimitador `\n`**: protocolo simples de framing em stream TCP.

# LeilãoNet — Frontend React/TypeScript

## Estrutura do Projeto

```
src/
├── types/
│   └── index.ts            # Tipos TypeScript que espelham o protocolo do backend
├── hooks/
│   └── useAuctionSocket.ts # Hook de WebSocket com reconexão automática
├── context/
│   └── AuctionContext.tsx  # Estado global (itens, logs, usuário) + dispatch de mensagens
├── pages/
│   ├── LoginPage.tsx       # Tela de registro (nome + modo admin/comprador)
│   ├── AdminPage.tsx       # Painel do administrador
│   └── BuyerPage.tsx       # Painel do comprador com lances em tempo real
├── App.tsx                 # Roteamento por papel (admin / comprador / login)
└── main.tsx                # Entry point React
```

## Fluxo de Dados

```
WebSocket (ws://localhost:6789)
        ↓
useAuctionSocket (hook)
        ↓
AuctionContext (estado global + handlers de mensagens)
        ↓
App → LoginPage | AdminPage | BuyerPage
```

## Instalação e execução

```bash
npm install
npm run dev       # http://localhost:3000
```

> **Pré-requisitos:** O backend (`server.py`) e o bridge (`ws_bridge.py`) devem estar rodando.

## Como usar

### Administrador
1. Informe um nome e marque **"Entrar como Administrador"**
2. Cadastre itens com nome, descrição e preço inicial
3. Acompanhe os lances em tempo real
4. Encerre leilões quando quiser — todos os compradores são notificados

### Comprador
1. Informe um nome (sem marcar admin)
2. Visualize os itens ativos e o lance atual
3. Digite um valor e clique **"Dar Lance"** (deve ser maior que o lance atual)
4. O painel ao vivo mostra todos os eventos em tempo real

## Variáveis de configuração

Edite `src/hooks/useAuctionSocket.ts` para alterar o endereço do bridge:

```ts
const WS_URL = 'ws://localhost:6789'
```
