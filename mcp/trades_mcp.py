import os
import sqlite3
from typing import TypedDict, Optional

from pydantic import BaseModel, Field

try:
    from config import config
    DB_PATH = config.DB_PATH
except Exception:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    FastMCP = None  # type: ignore

try:
    from sqlalchemy import create_engine, text
except Exception:
    create_engine = None  # type: ignore
    text = None  # type: ignore


class TradeModel(BaseModel):
    trade_id: str = Field(..., max_length=20)
    isin: str = Field(..., max_length=12)  # NOT NULL, references Product(isin)
    quantity: float = Field(..., description="DECIMAL(15,2) NOT NULL")
    trade_type: str = Field(..., max_length=4)  # CHECK (trade_type IN ('BUY', 'SELL'))
    client_account: str = Field(..., max_length=20)  # NOT NULL, references Client(client_account)
    trade_date: str = Field(...)  # DATE NOT NULL
    settlement_date: str = Field(...)  # DATE NOT NULL
    gross_credit: Optional[float] = Field(None, description="DECIMAL(15,2)")
    sales_person: Optional[str] = Field(None, max_length=50)
    trader: Optional[str] = Field(None, max_length=50)
    position_id: Optional[str] = Field(None, max_length=20)  # references Position(position_id)
    trader_charge: Optional[float] = Field(None, description="DECIMAL(10,2)")
    trade_price: float = Field(..., description="DECIMAL(10,4) NOT NULL")


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
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            return engine.connect()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_trades(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = """SELECT trade_id, isin, quantity, trade_type, client_account, trade_date,
            settlement_date, gross_credit, sales_person, trader, position_id, trader_charge, trade_price
            FROM trade ORDER BY trade_id LIMIT :limit OFFSET :offset"""
        conn = self._connect()
        try:
            if hasattr(conn, "execute") and text is not None:
                result = conn.execute(text(sql), {"limit": limit, "offset": offset})
                rows = [dict(r) for r in result.mappings().all()]
                conn.close()
                return rows
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute(sql.replace(":limit", "?").replace(":offset", "?"), (limit, offset))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_trade(self, trade_id: str) -> Optional[dict]:
        sql = "SELECT * FROM trades WHERE trade_id = :trade_id"
        conn = self._connect()
        try:
            if hasattr(conn, "execute") and text is not None:
                result = conn.execute(text(sql), {"trade_id": trade_id})
                row = result.mappings().first()
                conn.close()
                return dict(row) if row else None
        except Exception:
            pass
        cur = conn.cursor()
        cur.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None


store = TradeStore()
mcp = FastMCP("Trades MCP") if FastMCP is not None else None


def _to_trade_model(row: dict) -> TradeModel:
    return TradeModel(
        trade_id=row["trade_id"],
        isin=row["isin"],
        quantity=float(row["quantity"]),
        trade_type=row["trade_type"],
        client_account=row["client_account"],
        trade_date=row["trade_date"],
        settlement_date=row["settlement_date"],
        gross_credit=float(row["gross_credit"]) if row.get("gross_credit") else None,
        sales_person=row.get("sales_person"),
        trader=row.get("trader"),
        position_id=row.get("position_id"),
        trader_charge=float(row["trader_charge"]) if row.get("trader_charge") else None,
        trade_price=float(row["trade_price"])
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
