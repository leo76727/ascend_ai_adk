import os
import sqlite3
from typing import TypedDict, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text

try:
    from ..config import config
    DB_PATH = config.DB_PATH
except Exception:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))

class MTMModel(BaseModel):
    """Structured representation of an MTM record."""
    isin: str = Field(..., max_length=12)  # NOT NULL, references Product(isin)
    trade_date: str = Field(...)  # DATE NOT NULL
    trade_price: float = Field(..., description="DECIMAL(10,4) NOT NULL")
    mtm_price: float = Field(..., description="DECIMAL(10,4) NOT NULL")
    pnl: float = Field(..., description="DECIMAL(15,2) NOT NULL")


class MTMResponse(BaseModel):
    count: int
    mtm_records: list[MTMModel]


class MTMStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            return engine.connect()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_mtm(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sql = """
            SELECT isin, trade_date, trade_price, mtm_price, pnl
            FROM mtm 
            ORDER BY trade_date DESC, isin 
            LIMIT :limit OFFSET :offset
        """
        conn = self._connect()
        
        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                cur.execute(sql.replace(":limit", "?").replace(":offset", "?"), (limit, offset))
                rows = cur.fetchall()
                conn.close()
                return [dict(r) for r in rows]
            except Exception:
                conn.close()
                return []
        
        # SQLAlchemy path
        try:
            result = conn.execute(text(sql), {"limit": limit, "offset": offset})
            rows = [dict(r) for r in result.mappings().all()]
            conn.close()
            return rows
        except Exception:
            conn.close()
            return []

    def get_mtm(self, isin: str, trade_date: str) -> Optional[dict]:
        sql = "SELECT * FROM mtm WHERE isin = :isin AND trade_date = :trade_date"
        conn = self._connect()
        
        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM mtm WHERE isin = ? AND trade_date = ?", (isin, trade_date))
                row = cur.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception:
                conn.close()
                return None
                
        # SQLAlchemy path
        try:
            result = conn.execute(text(sql), {"isin": isin, "trade_date": trade_date})
            row = result.mappings().first()
            conn.close()
            return dict(row) if row else None
        except Exception:
            conn.close()
            return None


store = MTMStore()
mcp = FastMCP("MTM MCP")


def _to_mtm_model(row: dict) -> MTMModel:
    return MTMModel(
        isin=row["isin"],
        trade_date=row["trade_date"],
        trade_price=float(row["trade_price"]),
        mtm_price=float(row["mtm_price"]),
        pnl=float(row["pnl"])
    )


@mcp.tool()
def list_mtm(limit: int = 100, offset: int = 0) -> MTMResponse:
    """List MTM records with pagination."""
    rows = store.list_mtm(limit=limit, offset=offset)
    models = [_to_mtm_model(r) for r in rows]
    return MTMResponse(count=len(models), mtm_records=models)

@mcp.tool()
def get_mtm(isin: str, trade_date: str) -> Optional[MTMModel]:
    """Get MTM record by ISIN and trade date."""
    row = store.get_mtm(isin, trade_date)
    return _to_mtm_model(row) if row else None

__all__ = ["mcp", "store", "list_mtm", "get_mtm"]

def main():
    """Entry point for the direct execution server."""
    mcp.run()


if __name__ == "__main__":
    main()