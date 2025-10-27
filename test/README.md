Test with MCP HTTP Server Test
For a simple test of the MCP servers without FastMCP, you can run the test HTTP server:
```powershell
python mcp/mcp_http_server_test.py
```
This starts a basic HTTP server on port 8000 that exposes the MCP functions.

Test with MCP Inspector
To visually inspect and test the MCP servers, you can use the MCP Inspector tool:

1. First, ensure you have Node.js and npm installed
2. Run the MCP Inspector:
```powershell
npx @modelcontextprotocol/inspector
```
This will open the MCP Inspector in your default browser. By default, it connects to `http://localhost:8000`.

3. In the Inspector:
   - Click "Add Connection" to add a new MCP server connection
   - Enter the URL of your running MCP server (e.g., `http://localhost:8001` for the test server or `http://localhost:8003` for the actual position and others FastMCP server)
   - You can now browse and test all available MCP functions through the Inspector interface