import requests
import uuid
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"

def get_agent_response(agent_name, user_id, session_id, user_text):
    """
    Sends a query to the ADK agent's /run endpoint.
    """
    endpoint = f"{BASE_URL}/run"
    
    # Construct the payload strictly according to ADK REST API standards
    payload = {
        "app_name": agent_name,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": user_text}]
        }
    }

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        # The API returns a list of events. We need to parse them to find the agent's text.
        events = response.json()
        
        agent_text = ""
        
        # Iterate through events to find the final text response
        for event in events:
            # Check if the event has content and parts
            if "content" in event and "parts" in event["content"]:
                for part in event["content"]["parts"]:
                    if "text" in part:
                        agent_text += part["text"]
                        
        if not agent_text:
            return "[No text response received from agent]"
            
        return agent_text

    except requests.exceptions.ConnectionError:
        print(f"\nError: Could not connect to {BASE_URL}. Is 'adk api_server' running?")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        return f"HTTP Error: {e.response.text}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def create_session(agent_name, user_id, session_id):
    """
    Explicitly initializes a session. This is often required before /run calls.
    Endpoint: POST /apps/{app_name}/users/{user_id}/sessions/{session_id}
    """
    url = f"{BASE_URL}/apps/{agent_name}/users/{user_id}/sessions/{session_id}"
    try:
        # We send an empty dict or minimal body just to trigger creation
        requests.post(url, json={}) 
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {BASE_URL}. Is 'adk api_server' running?")
        sys.exit(1)

def main():
    print("--- ADK Local Agent Client ---")
    
    # Get the agent name (usually the folder name of your agent)
    if len(sys.argv) > 1:
        agent_name = sys.argv[1]
    else:
        agent_name = input("Enter your Agent's App Name (e.g., 'my_agent'): ").strip()

    if not agent_name:
        print("Agent name is required.")
        return

    # Generate random IDs for this interaction session
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    print(f"\nInitializing session '{session_id}' for agent '{agent_name}'...")
    create_session(agent_name, user_id, session_id)
    print("Session ready. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
            
            if not user_input.strip():
                continue

            response = get_agent_response(agent_name, user_id, session_id, user_input)
            print(f"Agent: {response}\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()