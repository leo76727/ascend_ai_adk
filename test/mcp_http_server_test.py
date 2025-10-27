"""
Example showing how to mount multiple StreamableHTTP servers with path configuration.

Run from the repository root:
    uvicorn examples.snippets.servers.streamable_http_multiple_servers:app --reload
"""

import contextlib
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.cors import CORSMiddleware  # Import added

from mcp.server.fastmcp import FastMCP
import uvicorn

# Create multiple MCP servers
api_mcp = FastMCP("API Server", stateless_http=True)
chat_mcp = FastMCP("Chat Server", stateless_http=True)


@api_mcp.tool()
def api_status() -> str:
    """Get API status"""
    return "API is running"


@chat_mcp.tool()
def send_message(message: str) -> str:
    """Send a chat message"""
    return f"Message sent: {message}"


# Configure servers to mount at the root of each path
# This means endpoints will be at /api and /chat instead of /api/mcp and /chat/mcp
api_mcp.settings.streamable_http_path = "/"
chat_mcp.settings.streamable_http_path = "/"
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(api_mcp.session_manager.run())
        await stack.enter_async_context(chat_mcp.session_manager.run())
        yield

# Mount the servers
app = Starlette(
    routes=[
        Mount("/api", app=api_mcp.streamable_http_app()),
        Mount("/chat", app=chat_mcp.streamable_http_app()),
    ],
    lifespan=lifespan
)

starlette_app = CORSMiddleware(
    app,
    allow_origins=["*"],  # Configure appropriately for production
    allow_methods=["GET", "POST", "DELETE"],  # MCP streamable HTTP methods
    expose_headers=["Mcp-Session-Id"],
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=8001) # Host on a different port