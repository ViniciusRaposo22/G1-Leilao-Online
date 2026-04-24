"""
auction_manager.py
------------------
Gerencia o estado dos leilões: itens, lances e regras de negócio.
Thread-safe via RLock para acesso concorrente de múltiplas conexões.

Persistência
------------
Ao encerrar um leilão, o registro completo é gravado em disco como:

    auctions/auction_<ITEM_ID>_<TIMESTAMP>.json

O arquivo contém o item (estado final), todo o histórico de lances e
os metadados de abertura/encerramento.
"""

import json
import uuid
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from protocol import AuctionItem, Bid

log = logging.getLogger("AuctionManager")

# Diretório onde os registros de leilão encerrado serão salvos.
AUCTIONS_DIR = Path("auctions")


class AuctionManager:
    """
    Repositório central de estado do leilão.
    Todas as operações são protegidas por RLock (reentrant lock)
    para garantir consistência em ambiente multithread.
    """

    def __init__(self, auctions_dir: Path = AUCTIONS_DIR):
        self._lock = threading.RLock()
        self._items: Dict[str, AuctionItem] = {}      # item_id → AuctionItem
        self._bid_history: Dict[str, List[Bid]] = {}  # item_id → [Bid, ...]
        self._opened_at: Dict[str, str] = {}          # item_id → ISO timestamp de criação

        self._auctions_dir = auctions_dir
        self._auctions_dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────
    #  Itens
    # ─────────────────────────────────────────

    def add_item(
        self,
        name: str,
        description: str,
        starting_price: float,
        image_base64: Optional[str] = None,
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
                image_base64=image_base64,
            )
            self._items[item_id] = item
            self._bid_history[item_id] = []
            self._opened_at[item_id] = datetime.now().isoformat(timespec="seconds")
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
        Encerra o leilão de um item e persiste o histórico em disco.

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

            # Grava o registro histórico em disco (fora do lock para não
            # bloquear outras operações durante I/O, mas copiamos os dados
            # necessários enquanto ainda estamos dentro do lock).
            history_snapshot = list(self._bid_history.get(item_id, []))
            opened_at = self._opened_at.get(item_id, "")

        # I/O fora do lock
        self._persist_auction(item, history_snapshot, opened_at)

        return True, "Leilão encerrado com sucesso.", item

    # ─────────────────────────────────────────
    #  Persistência
    # ─────────────────────────────────────────

    def _persist_auction(
        self,
        item: AuctionItem,
        history: List[Bid],
        opened_at: str,
    ) -> None:
        """
        Grava o registro completo do leilão encerrado em um arquivo JSON.

        Formato do arquivo:
        {
            "auction_id":    "<ITEM_ID>",
            "item":          { ...AuctionItem... },
            "opened_at":     "2025-01-01T10:00:00",
            "closed_at":     "2025-01-01T11:30:00",
            "total_bids":    5,
            "winner":        "Alice",
            "final_price":   350.00,
            "bid_history":   [ { ...Bid... }, ... ]
        }
        """
        closed_at = datetime.now().isoformat(timespec="seconds")
        timestamp_slug = closed_at.replace(":", "-").replace("T", "_")

        record = {
            "auction_id":  item.item_id,
            "item":        item.to_dict(),
            "opened_at":   opened_at,
            "closed_at":   closed_at,
            "total_bids":  len(history),
            "winner":      item.current_winner or "Nenhum lance recebido",
            "final_price": item.current_price,
            "bid_history": [b.to_dict() for b in history],
        }

        filename = self._auctions_dir / f"auction_{item.item_id}_{timestamp_slug}.json"

        try:
            filename.write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log.info(f"Histórico do leilão {item.item_id} salvo em '{filename}'.")
        except OSError as exc:
            log.error(f"Falha ao persistir leilão {item.item_id}: {exc}")