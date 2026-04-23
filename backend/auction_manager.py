"""
auction_manager.py
------------------
Gerencia o estado dos leilões: itens, lances e regras de negócio.
Thread-safe via RLock para acesso concorrente de múltiplas conexões.
"""

import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from protocol import AuctionItem, Bid


class AuctionManager:
    """
    Repositório central de estado do leilão.
    Todas as operações são protegidas por RLock (reentrant lock)
    para garantir consistência em ambiente multithread.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._items: Dict[str, AuctionItem] = {}      # item_id → AuctionItem
        self._bid_history: Dict[str, List[Bid]] = {}  # item_id → [Bid, ...]

    # ─────────────────────────────────────────
    #  Itens
    # ─────────────────────────────────────────

    def add_item(
        self,
        name: str,
        description: str,
        starting_price: float,
    ) -> AuctionItem:
        """Cadastra um novo item de leilão e retorna o objeto criado."""
        with self._lock:
            item_id = str(uuid.uuid4())[:8].upper()
            item = AuctionItem(
                item_id=item_id,
                name=name,
                description=description,
                starting_price=starting_price,
                current_price=starting_price,
                current_winner=None,
                is_active=True,
            )
            self._items[item_id] = item
            self._bid_history[item_id] = []
            return item

    def get_item(self, item_id: str) -> Optional[AuctionItem]:
        with self._lock:
            return self._items.get(item_id)

    def list_active_items(self) -> List[AuctionItem]:
        with self._lock:
            return [i for i in self._items.values() if i.is_active]

    def list_all_items(self) -> List[AuctionItem]:
        with self._lock:
            return list(self._items.values())

    # ─────────────────────────────────────────
    #  Lances
    # ─────────────────────────────────────────

    def place_bid(
        self,
        item_id: str,
        bidder: str,
        amount: float,
    ) -> Tuple[bool, str, Optional[Bid]]:
        """
        Tenta registrar um lance.

        Retorna:
            (success: bool, reason: str, bid: Optional[Bid])
        """
        with self._lock:
            item = self._items.get(item_id)

            if item is None:
                return False, "Item não encontrado.", None

            if not item.is_active:
                return False, "Este leilão já foi encerrado.", None

            if amount <= item.current_price:
                return (
                    False,
                    f"Lance deve ser maior que o atual "
                    f"(R$ {item.current_price:.2f}).",
                    None,
                )

            # Lance válido — atualiza estado
            bid = Bid(
                item_id=item_id,
                bidder=bidder,
                amount=amount,
                timestamp=datetime.now().isoformat(timespec="seconds"),
            )
            item.current_price = amount
            item.current_winner = bidder
            self._bid_history[item_id].append(bid)

            return True, "Lance aceito.", bid

    def get_bid_history(self, item_id: str) -> List[Bid]:
        with self._lock:
            return list(self._bid_history.get(item_id, []))

    # ─────────────────────────────────────────
    #  Encerramento
    # ─────────────────────────────────────────

    def close_auction(
        self, item_id: str
    ) -> Tuple[bool, str, Optional[AuctionItem]]:
        """
        Encerra o leilão de um item.

        Retorna:
            (success: bool, reason: str, item: Optional[AuctionItem])
        """
        with self._lock:
            item = self._items.get(item_id)

            if item is None:
                return False, "Item não encontrado.", None

            if not item.is_active:
                return False, "Leilão já estava encerrado.", None

            item.is_active = False
            return True, "Leilão encerrado com sucesso.", item