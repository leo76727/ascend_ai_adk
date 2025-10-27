import os
import sqlite3
from typing import TypedDict, Optional

from pydantic import BaseModel

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None  # type: ignore


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))


class TradeModel(BaseModel):
    trade_id: str
    client_account: Optional[str] = None
    product_id: Optional[str] = None
    quantity: Optional[int] = None
    trade_type: Optional[str] = None
    trade_price: Optional[float] = None
    trade_date: Optional[str] = None
    settlement_date: Optional[str] = None
    notional: Optional[float] = None
    currency: Optional[str] = None


class TradesResponse(BaseModel):
    count: int
    trades: list[TradeModel]


class TradeInfo(TypedDict):
    trade_id: str
    product_id: str

class TradeStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_trades(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = "SELECT * FROM trades ORDER BY trade_id LIMIT ? OFFSET ?"
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(sql, (limit, offset))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_trade(self, trade_id: str) -> Optional[dict]:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None


store = TradeStore()
mcp = FastMCP("Trades MCP") if FastMCP is not None else None


def _to_trade_model(row: dict) -> TradeModel:
    return TradeModel(
        trade_id=row.get("trade_id"),
        client_account=row.get("client_account"),
        product_id=row.get("product_id"),
        quantity=row.get("quantity"),
        trade_type=row.get("trade_type"),
        trade_price=row.get("trade_price"),
        trade_date=row.get("trade_date"),
        settlement_date=row.get("settlement_date"),
        notional=row.get("notional"),
        currency=row.get("currency"),
    )


if mcp is not None:
    @mcp.tool()
    def list_trades(limit: int = 100, offset: int = 0) -> TradesResponse:
        rows = store.list_trades(limit=limit, offset=offset)
        models = [_to_trade_model(r) for r in rows]
        return TradesResponse(count=len(models), trades=models)


    @mcp.tool()
    def get_trade(trade_id: str) -> Optional[TradeModel]:
        row = store.get_trade(trade_id)
        return _to_trade_model(row) if row else None


    @mcp.tool()
    def get_trade_info(trade_id: str) -> Optional[TradeInfo]:
        row = store.get_trade(trade_id)
        if not row:
            return None
        return TradeInfo(trade_id=row["trade_id"], product_id=row.get("product_id"))  # type: ignore[arg-type]


else:
    def list_trades(limit: int = 100, offset: int = 0) -> TradesResponse:
        rows = store.list_trades(limit=limit, offset=offset)
        models = [_to_trade_model(r) for r in rows]
        return TradesResponse(count=len(models), trades=models)


    def get_trade(trade_id: str) -> Optional[TradeModel]:
        row = store.get_trade(trade_id)
        return _to_trade_model(row) if row else None


    def get_trade_info(trade_id: str) -> Optional[TradeInfo]:
        row = store.get_trade(trade_id)
        if not row:
            return None
        return TradeInfo(trade_id=row["trade_id"], product_id=row.get("product_id"))  # type: ignore[arg-type]


__all__ = ["mcp", "store", "list_trades", "get_trade", "get_trade_info"]
