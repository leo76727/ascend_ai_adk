import os
import sys
from google.adk.agents import Agent, callback_context
from google.adk.models import LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from pathlib import Path

# Ensure the repository root (parent of the `agents` folder) is on sys.path so
# top-level imports like `import config` work when this script is run from
# inside the `agents/` directory. We insert it at the front so it takes
# precedence over other paths.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import config

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

root_agent = Agent(
    name="trader_manager_agent",
    instruction=config.PROMPT_TEMPLATES["trader_manager"]["prompt"],
    model=LiteLlm(model=config.LLM_PROVIDER),  #DeepseekModel(),
    tools=[client_tool, position_tool, quote_tool, market_tool, product_tool],
)
