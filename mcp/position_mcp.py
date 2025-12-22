import os
import sqlite3
from typing import TypedDict, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

try:
    from config import config
    DB_PATH = config.DB_PATH
except Exception:
    DB_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "positions.db")
    )
class PositionModel(BaseModel):
    """Structured representation of a position record."""
    position_id: str = Field(..., max_length=20)
    isin: str = Field(..., max_length=12)  # NOT NULL, references Product(isin)
    quantity: float = Field(..., description="DECIMAL(15,2) NOT NULL")
    client_account: str = Field(..., max_length=20)  # NOT NULL, references Client(client_account)
    expiration_date: Optional[str] = None  # DATE, nullable


class PositionsResponse(BaseModel):
    count: int
    positions: list[PositionModel]


# A small TypedDict example (also structured but simpler than Pydantic)
class PositionInfo(TypedDict):
    id: int
    client_id: str
    product_id: str
    quantity: int


class PositionStore:
    """SQLite-backed access to the `positions` table."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            return engine.connect()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_positions(
        self,
        limit: int = 100,
        offset: int = 0,
        client_id: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> list[dict]:
        q = [
            "SELECT position_id, isin, quantity, client_account, expiration_date",
            "FROM position",
        ]
        params: dict = {"limit": limit, "offset": offset}
        clauses: list[str] = []
        if client_id:
            clauses.append("client_id = :client_id")
            params["client_id"] = client_id
        if product_id:
            clauses.append("product_id = :product_id")
            params["product_id"] = product_id
        if clauses:
            q.append("WHERE " + " AND ".join(clauses))
        q.append("ORDER BY id LIMIT :limit OFFSET :offset")
        sql = " ".join(q)
        conn = self._connect()

        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                # convert named params to positional for sqlite
                sqlite_sql = sql.replace(":client_id", "?").replace(":product_id", "?").replace(":limit", "?").replace(":offset", "?")
                positional: list = []
                if client_id:
                    positional.append(client_id)
                if product_id:
                    positional.append(product_id)
                positional.extend([limit, offset])
                
                cur.execute(sqlite_sql, tuple(positional))
                rows = cur.fetchall()
                conn.close()
                return [dict(r) for r in rows]
            except Exception:
                conn.close()
                return []
        
        # SQLAlchemy path
        try:
            result = conn.execute(text(sql), params)
            rows = [dict(r) for r in result.mappings().all()]
            conn.close()
            return rows
        except Exception:
            conn.close()
            return []

    def get_position(self, position_id: int) -> Optional[dict]:
        sql = "SELECT * FROM positions WHERE id = :id"
        conn = self._connect()
        
        if isinstance(conn, sqlite3.Connection):
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
                row = cur.fetchone()
                conn.close()
                return dict(row) if row else None
            except Exception:
                conn.close()
                return None
        
        # SQLAlchemy path
        try:
            result = conn.execute(text(sql), {"id": position_id})
            row = result.mappings().first()
            conn.close()
            return dict(row) if row else None
        except Exception:
            conn.close()
            return None


# Create FastMCP instance if available; otherwise expose same callables for
# external registration or local testing.
mcp = FastMCP("Position MCP")
store = PositionStore()

def _convert_row_to_position_model(row: dict) -> PositionModel:
    # Convert SQL row dict to Pydantic PositionModel (handles None safely)
    return PositionModel(
        position_id=row["position_id"],
        isin=row["isin"],
        quantity=float(row["quantity"]),
        client_account=row["client_account"],
        expiration_date=row.get("expiration_date"),
    )


@mcp.tool()
def list_positions(limit: int = 100, offset: int = 0, client_id: Optional[str] = None, product_id: Optional[str] = None) -> PositionsResponse:
    """Structured: returns PositionsResponse (Pydantic) with list of PositionModel."""
    rows = store.list_positions(limit=limit, offset=offset, client_id=client_id, product_id=product_id)
    models = [_convert_row_to_position_model(r) for r in rows]
    return PositionsResponse(count=len(models), positions=models)


@mcp.tool()
def get_position(position_id: int) -> Optional[PositionModel]:
    """Structured: returns a single PositionModel or None."""
    row = store.get_position(position_id)
    return _convert_row_to_position_model(row) if row else None


@mcp.tool()
def get_position_info(position_id: int) -> Optional[PositionInfo]:
    """TypedDict: simpler structure useful for lightweight clients."""
    row = store.get_position(position_id)
    if not row:
        return None
    return PositionInfo(id=row["id"], client_id=row["client_id"], product_id=row["product_id"], quantity=row["quantity"])  # type: ignore[call-arg]

@mcp.tool()
def list_positions_raw(limit: int = 100) -> dict:
    """Unstructured/dynamic: return raw dicts (flexible schema)."""
    rows = store.list_positions(limit=limit)
    return {"result": rows}

__all__ = [
    "mcp",
    "store",
    "list_positions",
    "get_position",
    "get_position_info",
    "list_positions_raw",
]

def main():
    """Entry point for the direct execution server."""
    mcp.run()


if __name__ == "__main__":
    main()