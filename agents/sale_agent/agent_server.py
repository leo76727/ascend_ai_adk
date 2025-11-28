import json
import re
import os
import traceback
from fastapi import FastAPI, Depends, HTTPException, status,Query
from fastapi.middleware.cors import CORSMiddleware
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from agent import root_agent
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, Header
from typing import Annotated, Union
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import logging
import uuid
import asyncio
import sys

bearer_scheme = HTTPBearer()

# Load environment variables from .env file
load_dotenv()

# Retrieve the database URL for sessions
#session_db_url = str(os.getenv("SESSION_DB"))

# Configure logging for the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_json_response(text: str) -> str:
    """
    Removes potential JSON markdown formatting (e.g., ```json\n...\n```)
    from LLM responses to ensure valid JSON parsing.
    """
    text = re.sub(r"^```json\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n```$", "", text, flags=re.MULTILINE)
    return text.strip()


async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    # In a real application, you would add token validation logic here
    # e.g., decoding a JWT, checking against a database, etc.
    # If validation fails, raise an HTTPException
    # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    print(f"Authenticated request with token: {token}")
    return token

# Initialize the FastAPI application
app = FastAPI()

# Initialize database session service
try:
    # Attempt to initialize DatabaseSessionService with the provided URL
    db_session_service = InMemorySessionService()
    #DatabaseSessionService(db_url=session_db_url) #InMemorySessionService is another choice
    #logger.info(f"DatabaseSessionService initialized with URL: {session_db_url[:50]}...")
except Exception as e:
    # Log and raise an error if database session service initialization fails
    logger.error(f"Failed to initialize DatabaseSessionService: {e}")
    raise

# Add CORS middleware to allow requests from any origin for development/testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers in the request
)

# Initialize the ADK Runner with the application name, root agent, and session service
runner = Runner(
    app_name="sales-agent-app",
    agent=root_agent,
    session_service=db_session_service,
)


@app.get("/sales-agent/")
async def process_sales_request(
    query: str = Query(
        ..., description="The natural language query for the sales agent"
    ),
    session_id: str = Query(default=None, description="Session ID for the request"),
    user_id: str = Query(default="default", description="User ID for the session"),
    token: str = Depends(get_current_user_token)
):
    """
    Processes the input query using the chart agent pipeline and attempts
    to return the final structured JSON output.
    """ 
    # Create or retrieve a session for the request
    try:
        session = await db_session_service.create_session(
            app_name="sales-agent-app", user_id=user_id, session_id=session_id, state = {"user:bearer_token": token}
        )
    except Exception as e:
        logger.error(f"Failed to create or retrieve session: {e}")
        session = await db_session_service.create_session(
            app_name="sales-agent-app", user_id=user_id, state = {"user:bearer_token": token}
        )    

    try:
        # Create a user message from the input query
        user_message = types.Content(role="user", parts=[types.Part(text=query)])
        final_response_text = None
        # Run the agent asynchronously and iterate through events
        async for event in runner.run_async(
            user_id=user_id, new_message=user_message, session_id=session.id
        ):
            # Capture the final response text when available
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[-1].text
                break

        # If no final response text was produced, raise an error
        if final_response_text is None:
            logger.error("Agent pipeline did not produce a final text response")
            raise HTTPException(
                status_code=500,
                detail="Agent pipeline did not produce a final text response.",
            )

        # Attempt to clean and parse the final text as JSON
        try:
            cleaned_response = clean_json_response(final_response_text)
            parsed_json = json.loads(cleaned_response)
            logger.info("Successfully parsed JSON response")
            return parsed_json
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            logger.error(f"JSON decode error: {e}")            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "The final agent response was not valid JSON.",
                    "raw_response": final_response_text,
                    "json_error": str(e),
                },
            )

    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    except Exception as e:
        # Catch and log unexpected errors, then raise an HTTPException
        logger.error(f"Unexpected error in chart request: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during processing: {str(e)}",
        )

@app.get("/health/")
async def health_check():
    """Basic health check endpoint to verify the API is running."""
    return {"status": "ok", "app_name": runner.app_name}



if __name__ == "__main__":
    import uvicorn

    # Run the FastAPI application using Uvicorn
    uvicorn.run(
        app, host="0.0.0.0", port=9010
    )  # Set reload=True for development