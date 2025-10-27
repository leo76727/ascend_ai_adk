import streamlit as st
import requests
import uuid

# --- Page Configuration ---
st.set_page_config(
    page_title="ADK + Deepseek Demo",
    page_icon="🤖"
)
st.title("🤖 ADK Agent Demo")
st.caption("Frontend: Streamlit | Backend: FastAPI (ADK + Deepseek) | Tool: MCP Server")

# Define the API endpoint for our agent server
AGENT_SERVER_URL = "http://127.0.0.1:8081/chat"

# --- Session State ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    print(f"New session created: {st.session_state.session_id}")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "How can I help you today?"}
    ]

# --- Helper Function to Call API ---
def get_agent_response(user_input, session_id):
    """Calls the backend agent API and returns the response."""
    payload = {
        "user_input": user_input,
        "session_id": session_id
    }
    try:
        response = requests.post(AGENT_SERVER_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return data["response"], data["interactions"]
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            return error_msg, [error_msg]
            
    except requests.exceptions.ConnectionError:
        error_msg = "Error: Cannot connect to the Agent Server. Is it running?"
        return error_msg, [error_msg]
    except Exception as e:
        error_msg = f"An unknown error occurred: {e}"
        return error_msg, [error_msg]

# --- Chat UI ---
# Display past chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display the interaction log for assistant messages
        if message["role"] == "assistant" and "interactions" in message:
            with st.expander("Agent Interactions"):
                st.markdown("\n\n".join(message["interactions"]), unsafe_allow_html=True)

# --- User Input ---
if prompt := st.chat_input("What is up?"):
    # 1. Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Get agent response via API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Thinking..."):
            
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