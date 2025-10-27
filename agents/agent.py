# Mock tool implementation
#def get_current_time(city: str) -> dict:
#    """Returns the current time in a specified city."""
#    return {"status": "success", "city": city, "time": "10:30 AM"}
#root_agent = Agent(
#    model=LiteLlm(model=config.LLM_PROVIDER),
#    name='root_agent',
#    description="Tells the current time in a specified city.",
#    instruction="You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.",
#    tools=[get_current_time],
#)

import os
from google.adk.agents import Agent, callback_context
from google.adk.models import LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from . import config

print(f"Config: {config.LLM_PROVIDER}, API Key: {config.DEEPSEEK_API_KEY}")
os.environ["DEEPSEEK_API_KEY"] = config.DEEPSEEK_API_KEY

# --- 1. Interaction Logger (Callbacks) ---
# We now log interactions into the session state, not a global variable.
def log_interaction(context: callback_context.CallbackContext, message: str):
    """Helper to add a message to the session's interaction log."""
    print(message) # For terminal debugging
    if "interaction_log" not in context.state:
        context.state["interaction_log"] = []
    context.state["interaction_log"].append(message)

# Define ADK Callbacks
def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
):
    log_interaction(callback_context, f"🧠 **Thinking...**\n(Sending to Deepseek LLM)")
    return llm_request

def before_tool_callback(
    context: callback_context.CallbackContext, llm_request: LlmRequest
):
    log_interaction(
        context,
        f"🛠️ **LLM Request Content:** `{llm_request.contents}`\n"
    )
    return llm_request

def after_tool_callback(
    context: callback_context.CallbackContext, tool_response: dict
):
    log_interaction(
        context,
        f"✔️ **Tool Response:**\n"
        f"   ```json\n{tool_response}\n   ```"
    )
    return tool_response

# --- 2. Custom LiteLLM Wrapper for Deepseek (Same as before) ---
"""Custom LiteLLM wrapper to call Deepseek API.
class DeepseekModel(Agent):
    async def generate_content(
        self, request: LlmRequest, **kwargs: Any
    ) -> LlmResponse:
        import litellm
        messages = [msg.to_dict() for msg in request.contents]
        
        system_prompt = None
        if messages[0]["role"] == "system":
            system_prompt = messages.pop(0)["parts"][0]["text"]

        response = await litellm.acompletion(
            model=LiteLlm(model=config.LLM_PROVIDER),
            messages=messages,
            system_prompt=system_prompt,
            api_key=config.DEEPSEEK_API_KEY,
            tools=[t.to_dict() for t in request.tools] if request.tools else None
        )
        
        choice = response.choices[0]
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            return LlmResponse(
                contents=[
                    agents.Content(
                        parts=[
                            agents.Part(
                                function_call=agents.FunctionCall(
                                    name=tool_call.function.name,
                                    args=tool_call.function.arguments_json_string
                                )
                            )
                        ]
                    )
                ]
            )
        else:
            return LlmResponse(
                contents=[
                    agents.Content(parts=[agents.Part(text=choice.message.content)])
                ]
            )
"""
# --- 3. Agent Definition (Same as before) ---
mcp_server_url = "http://127.0.0.1:8003/client"  # Adjust port if needed
client_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url
))
position_mcp_server_url = "http://127.0.0.1:8003/position"
position_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url
    )
)
quote_mcp_server_url = "http://127.0.0.1:8003/quote"
quote_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=quote_mcp_server_url
    )
)
market_mcp_server_url = "http://127.0.0.1:8003/market"  
market_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=market_mcp_server_url
    )
)
product_mcp_server_url = "http://127.0.0.1:8003/product"
product_tool = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=product_mcp_server_url
    )
)

print("Client tools: {client_tool.get_tools()}")
root_agent = Agent(
    name="sales_manager_agent",
    instruction=config.PROMPT_TEMPLATES["sales_manager"]["prompt"],
    model=LiteLlm(model=config.LLM_PROVIDER),  #DeepseekModel(),
    tools=[client_tool, position_tool, quote_tool, market_tool, product_tool],
)


"""
# --- 4. FastAPI Server ---
app = FastAPI(
    title="ADK Agent Server",
    description="Exposes the Google ADK Agent as a REST API."
)

# In-memory session service for the agent
session_service = sessions.InMemorySessionService()
root_agent = get_chat_agent()

agent_runner = Runner(
    app_name="ascend_ai_adk_agent_runner",
    agent=root_agent,
    session_service=session_service,
)

# Define request and response models
class ChatRequest(BaseModel):
    user_input: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    interactions: List[str]
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        print(f"Received chat request: {request}")
        # Get the session, which stores memory and our interaction_log
        session = await session_service.get_session(
            app_name="ascend_ai_adk_agent_runner",
            user_id="user1",
            session_id=request.session_id
            )
        if not session:
            session = await session_service.create_session(app_name="ascend_ai_adk_agent_runner",
                                                     user_id="user1", 
                                                     session_id=str(uuid.uuid4()).replace("-", ""))
            
            
        # CRITICAL: Clear the interaction log for this new turn
        session.state["interaction_log"] = []
        content = types.Content(role='user', parts=[types.Part(text=request.user_input)])

        # Run the agent
        async for event in agent_runner.run_async(user_id="user1", 
                                            session_id=session.id, 
                                            new_message=content):
      # You can uncomment the line below to see *all* events during execution
            print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Assuming text response in the first part
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate: # Handle potential errors/escalations
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                # Add more checks here if needed (e.g., specific error codes)
                break # Stop processing events once the final response is found

#        final_response = await root_agent.run_async(
#            user_input=request.user_input,
#            session_id=session.id
#        )

        response_text = final_response.parts[0].text or ""
        
        # Log the final answer
        log_interaction(
            agent_runner.get_run_context(session.id), 
            f"✅ **Final Answer:**\n{response_text}"
        )
        
        # Get the log from the session state
        interactions = session.state.get("interaction_log", [])
        
        return ChatResponse(
            response=response_text,
            interactions=interactions,
            session_id=session.id
        )

    except Exception as e:
        print(f"Agent run error: {e}")
        return ChatResponse(
            response=f"Sorry, an error occurred: {e}",
            interactions=[f"❌ **Error:**\n{e}"],
            session_id=request.session_id
        )
"""

"""
This is the main entry point for the agent.
"""
"""
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    print(f"🚀 Starting ADK Agent Server on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
"""