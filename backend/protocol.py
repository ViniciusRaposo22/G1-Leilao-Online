"""
protocol.py
-----------
Define todos os tipos de mensagem e estruturas do protocolo de comunicação
do sistema de leilão. Toda comunicação é feita via JSON serializado sobre TCP.
"""

import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional


# ─────────────────────────────────────────────
#  Tipos de Mensagem (Cliente → Servidor)
# ─────────────────────────────────────────────

class ClientMessageType(str, Enum):
    REGISTER       = "REGISTER"        # Registrar participante com nome
    ADD_ITEM       = "ADD_ITEM"        # Cadastrar item de leilão (admin)
    PLACE_BID      = "PLACE_BID"       # Enviar lance
    CLOSE_AUCTION  = "CLOSE_AUCTION"   # Encerrar leilão do item (admin)
    LIST_ITEMS     = "LIST_ITEMS"      # Listar itens disponíveis
    PING           = "PING"            # Heartbeat


# ─────────────────────────────────────────────
#  Tipos de Mensagem (Servidor → Cliente)
# ─────────────────────────────────────────────

class ServerMessageType(str, Enum):
    WELCOME         = "WELCOME"         # Confirmação de registro
    ITEM_ADDED      = "ITEM_ADDED"      # Novo item cadastrado
    BID_ACCEPTED    = "BID_ACCEPTED"    # Lance aceito e broadcast
    BID_REJECTED    = "BID_REJECTED"    # Lance rejeitado (valor inválido)
    AUCTION_CLOSED  = "AUCTION_CLOSED"  # Leilão encerrado + vencedor
    ITEMS_LIST      = "ITEMS_LIST"      # Lista de itens ativos
    ERROR           = "ERROR"           # Erro genérico
    PONG            = "PONG"            # Resposta ao heartbeat
    NOTIFICATION    = "NOTIFICATION"    # Notificação geral


# ─────────────────────────────────────────────
#  Estruturas de Dados
# ─────────────────────────────────────────────

@dataclass
class AuctionItem:
    item_id: str
    name: str
    description: str
    starting_price: float
    current_price: float
    current_winner: Optional[str]   # nome do comprador líder
    is_active: bool
    image_base64: Optional[str] = None   # imagem do item em base64 (opcional)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Bid:
    item_id: str
    bidder: str
    amount: float
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────
#  Funções de serialização / desserialização
# ─────────────────────────────────────────────

DELIMITER = b"\n"   # separador de mensagens no stream TCP


def encode_message(msg_type: str, payload: dict) -> bytes:
    """Serializa uma mensagem para envio via socket."""
    message = json.dumps({"type": msg_type, "payload": payload})
    return (message + "\n").encode("utf-8")


def decode_message(raw: str) -> dict:
    """Desserializa uma mensagem recebida do socket."""
    return json.loads(raw.strip())


def build_client_message(msg_type: ClientMessageType, **kwargs) -> bytes:
    return encode_message(msg_type.value, kwargs)


def build_server_message(msg_type: ServerMessageType, **kwargs) -> bytes:
    return encode_message(msg_type.value, kwargs)