import os
import sqlite3
from typing import TypedDict, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import Context, FastMCP
from fastmcp.server.dependencies import get_http_headers

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MyMCPApp")

try:
    # Prefer config-driven DB path; config may point to sqlite or a postgres URL
    from config import config
    DB_PATH = config.DB_PATH
except Exception:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "positions.db"))


try:
    # optional dependency for Postgres support
    from sqlalchemy import create_engine, text
except Exception:
    create_engine = None  # type: ignore
    text = None  # type: ignore

class ClientModel(BaseModel):
    client_id: str = Field(..., max_length=20)
    client_name: str = Field(..., max_length=100)  # NOT NULL in schema
    client_account: str = Field(..., max_length=20)  # NOT NULL and UNIQUE in schema


class ClientsResponse(BaseModel):
    count: int
    clients: list[ClientModel]


class ClientInfo(TypedDict):
    client_id: str
    client_name: str

class ClientStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _connect(self):
        """Return a DB connection object.

        - For sqlite: return a sqlite3.Connection with row_factory
        - For SQLAlchemy-based URLs (postgres): return a SQLAlchemy connection
        """
        if isinstance(self.db_path, str) and (self.db_path.startswith("postgres") or "://" in self.db_path and not self.db_path.endswith(".db")) and create_engine is not None:
            engine = create_engine(self.db_path)
            conn = engine.connect()
            return conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_clients(self, limit: int = 100, offset: int = 0, headers: dict = {}) -> list[dict]:
        logger.info(f"*****{headers}*****")
        sql = "SELECT client_id, client_name, client_account FROM client ORDER BY client_id LIMIT :limit OFFSET :offset"
        conn = self._connect()
        try:
            auth_header = headers.get("Authorization") if headers else None
            logger.info(f"********Auth header in list_clients: {auth_header}")
            
            if isinstance(conn, sqlite3.Connection):
                cur = conn.cursor()
                cur.execute(sql.replace(":limit", "?" ).replace(":offset", "?"), (limit, offset))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            else:
                # SQLAlchemy connection
                if text is None:
                    raise ImportError("SQLAlchemy is not installed or failed to load.")
                result = conn.execute(text(sql), {"limit": limit, "offset": offset})
                rows = [dict(r) for r in result.mappings().all()]
                return rows
        finally:
            conn.close()

    def get_client(self, client_id: str) -> Optional[dict]:
        sql = "SELECT * FROM client WHERE client_id = :client_id"
        conn = self._connect()
        try:
            if isinstance(conn, sqlite3.Connection):
                cur = conn.cursor()
                cur.execute("SELECT * FROM client WHERE client_id = ?", (client_id,))
                row = cur.fetchone()
            else:
                # SQLAlchemy connection
                if text is None:
                    raise ImportError("SQLAlchemy is not installed or failed to load.")
                result = conn.execute(text(sql), {"client_id": client_id})
                row = result.mappings().first()
                
            return dict(row) if row else None
        finally:
            conn.close()

# Create multiple MCP servers
store = ClientStore()
client_mcp_server = FastMCP("Clients MCP", stateless_http=True)

def _to_client_model(row: dict) -> ClientModel:
    return ClientModel(
        client_id=row["client_id"],
        client_name=row["client_name"],
        client_account=row["client_account"],
        #client_address=row.get("client_address"),
    )

@client_mcp_server.tool()
def list_clients(limit: int = 100, offset: int = 0) -> ClientsResponse:
        headers = get_http_headers(include_all=True)
        logger.info(f"********Headers in list_clients: {headers}*******")
        """List clients with pagination."""
        rows = store.list_clients(limit=limit, offset=offset, headers=headers)
        models = [_to_client_model(r) for r in rows]
        return ClientsResponse(count=len(models), clients=models)


@client_mcp_server.tool()
def get_client(client_id: str) -> Optional[ClientModel]:
    """Get a client by client_id."""
    row = store.get_client(client_id)
    return _to_client_model(row) if row else None


@client_mcp_server.tool()
def get_client_info(client_id: str) -> Optional[ClientInfo]:
    """Get basic client info by client_id."""
    row = store.get_client(client_id)
    if not row:
        return None
    return ClientInfo(client_id=row["client_id"], client_name=row.get("client_name"))  # type: ignore[arg-type]

__all__ = ["client_mcp_server", "store", "list_clients", "get_client", "get_client_info"]
def main():
    """Entry point for the direct execution server."""
    client_mcp_server.run()


if __name__ == "__main__":
    main()