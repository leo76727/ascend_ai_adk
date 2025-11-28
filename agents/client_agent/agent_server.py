import json
import re
import os
import traceback
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from agent import client_agent
from google.genai import types
from dotenv import load_dotenv
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

bearer_scheme = HTTPBearer()

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_json_response(text: str) -> str:
    text = re.sub(r"^```json\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```$", "", text, flags=re.MULTILINE)
    return text.strip()

async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    return token

app = FastAPI()

try:
    db_session_service = InMemorySessionService()
except Exception as e:
    logger.error(f"Failed to initialize DatabaseSessionService: {e}")
    raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = Runner(
    app_name="client-agent-app",
    agent=client_agent,
    session_service=db_session_service,
)

@app.get("/client-agent/")
async def process_client_request(
    query: str = Query(..., description="The natural language query for the client agent"),
    session_id: str = Query(default=None, description="Session ID"),
    user_id: str = Query(default="default", description="User ID"),
    token: str = Depends(get_current_user_token)
):
    try:
        try:
            session = await db_session_service.create_session(
                app_name="client-agent-app", user_id=user_id, session_id=session_id, state = {"user:bearer_token": token}
            )
        except Exception as e:
            logger.error(f"Failed to create or retrieve session: {e}")
            session = await db_session_service.create_session(
                app_name="client-agent-app", user_id=user_id, state = {"user:bearer_token": token}
            )    

        user_message = types.Content(role="user", parts=[types.Part(text=query)])
        final_response_text = None
        
        async for event in runner.run_async(
            user_id=user_id, new_message=user_message, session_id=session.id
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[-1].text
                break

        if final_response_text is None:
            raise HTTPException(status_code=500, detail="Agent pipeline did not produce a final text response.")

        # Try to parse as JSON if it looks like JSON, otherwise return text wrapped in JSON
        try:
            cleaned_response = clean_json_response(final_response_text)
            if cleaned_response.startswith("{") or cleaned_response.startswith("["):
                 parsed_json = json.loads(cleaned_response)
                 return parsed_json
            else:
                 return {"response": final_response_text}
        except json.JSONDecodeError:
             return {"response": final_response_text}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/health/")
async def health_check():
    return {"status": "ok", "app_name": runner.app_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9011) # Using port 9011 to avoid conflict with sale_agent
