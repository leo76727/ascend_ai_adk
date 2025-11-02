
import os
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
        agents_dir="agents",
        session_service_uri="sqlite:///memory.db", # Example session storage
        allow_origins=["*"], # Adjust as needed for CORS
        web=True, # Enable ADK's web interface if desired
        port=8081,        
    )

@app.get("/hello")
async def say_hello():
    return {"hello": "world"}

"""
This is the main entry point for the agent.
"""
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    print(f"🚀 Starting ADK Agent Server on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)