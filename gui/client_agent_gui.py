import streamlit as st
import requests
import uuid
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Client Intelligence Agent",
    page_icon="💼",
    layout="wide"
)

st.title("💼 Client Intelligence Agent")
st.caption("Powered by Google ADK & Deepseek")

# Define the API endpoint for our agent server
# Note: The client agent server is running on port 9011
AGENT_SERVER_URL = "http://127.0.0.1:9011/client-agent/"

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    # print(f"New session created: {st.session_state.session_id}")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your Client Intelligence Agent. I can help you analyze client portfolios, trading patterns, and suggest actionable insights. Which client would you like to discuss today?", "interactions": []}
    ]

# --- Helper Function to Call API ---
def get_agent_response(user_input, session_id):
    """Calls the backend agent API and returns the response."""
    # The agent server expects query parameters
    params = {
        "query": user_input,
        "session_id": session_id,
        "user_id": "streamlit_user" 
    }
    # For now, we are using a mock token or relying on the server to handle it. 
    # In a real app, you'd handle auth properly.
    headers = {"Authorization": "Bearer mock_token"}

    try:
        response = requests.get(AGENT_SERVER_URL, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # The server returns either a JSON object or a wrapped text response
            if isinstance(data, dict):
                if "response" in data:
                    return data["response"], [] # Simple text response
                else:
                    # If it's a structured JSON response (e.g. from the agent's analysis)
                    # We might want to format it nicely. For now, let's dump it as string
                    # or check if there's a specific field.
                    # The prompt template suggests markdown output, so it might be in a specific field 
                    # or just the whole body if the agent returned a dict.
                    # Let's assume the agent returns a dict that might need formatting.
                    return json.dumps(data, indent=2), []
            return str(data), []
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            return error_msg, [error_msg]
            
    except requests.exceptions.ConnectionError:
        error_msg = "Error: Cannot connect to the Agent Server. Is it running on port 9011?"
        return error_msg, [error_msg]
    except Exception as e:
        error_msg = f"An unknown error occurred: {e}"
        return error_msg, [error_msg]

# --- Chat UI ---
# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display the interaction log for assistant messages if we had them
        if message["role"] == "assistant" and "interactions" in message and message["interactions"]:
            with st.expander("Agent Interactions"):
                st.markdown("\n\n".join(message["interactions"]), unsafe_allow_html=True)

# --- User Input ---
if prompt := st.chat_input("Ask about a client..."):
    # 1. Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Get agent response via API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Analyzing..."):
            
            response_text, current_interactions = get_agent_response(
                prompt, st.session_state.session_id
            )
        
        # Display the final response
        message_placeholder.markdown(response_text)

    # 3. Add agent message and interactions to session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": response_text,
        "interactions": current_interactions
    })
