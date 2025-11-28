"""
Interactive script to query the FastAPI Sales Agent Server
Usage: python test_agent_server.py
"""

import requests
import json
import sys
import argparse
from typing import Optional


def query_agent(
    query: str,
    user_id: str,
    bearer_token: str,
    base_url: str = "http://localhost:9010",
    session_id: Optional[str] = None
):
    """
    Send a query to the sales agent endpoint
    
    Args:
        query: The question/query for the agent
        user_id: User identifier
        bearer_token: Authentication token
        base_url: Base URL of the API server
        session_id: Optional session ID for maintaining conversation context
    """
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    
    # Prepare query parameters
    params = {
        "query": query,
        "user_id": user_id
    }
    
    if session_id:
        params["session_id"] = session_id
    
    # Make the request
    try:
        print(f"\n{'='*80}")
        print(f"Sending query to: {base_url}/sales-agent/")
        print(f"User ID: {user_id}")
        print(f"Session ID: {session_id if session_id else 'New session'}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")
        
        response = requests.get(
            f"{base_url}/sales-agent/",
            params=params,
            headers=headers,
            timeout=60  # 60 second timeout
        )
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            result = response.json()
            print("Response:")
            print(json.dumps(result, indent=2))
            return result
        else:
            print(f"Error Response:")
            print(response.text)
            return None
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out after 60 seconds")
        return None
    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to {base_url}")
        print("  Make sure the server is running!")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def interactive_mode():
    """Run in interactive mode, prompting for inputs"""
    print("\n" + "="*80)
    print("  Sales Agent Interactive Client")
    print("="*80 + "\n")
    
    # Get base URL
    base_url = input("Enter API base URL [http://localhost:9010]: ").strip()
    if not base_url:
        base_url = "http://localhost:9010"
    
    # Get bearer token
    bearer_token = input("Enter bearer token: ").strip()
    if not bearer_token:
        print("✗ Bearer token is required!")
        sys.exit(1)
    
    # Get user ID
    user_id = input("Enter user ID [default-user]: ").strip()
    if not user_id:
        user_id = "default-user"
    
    # Optional session ID
    session_id = input("Enter session ID (press Enter for new session): ").strip()
    if not session_id:
        session_id = None
    
    print("\nEnter your questions below (type 'exit' or 'quit' to stop):\n")
    
    while True:
        try:
            query = input("Question: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye!")
                break
            
            if not query:
                print("Please enter a question.")
                continue
            
            query_agent(query, user_id, bearer_token, base_url, session_id)
            print("\n" + "-"*80 + "\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Query the FastAPI Sales Agent Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for all inputs)
  python test_agent_server.py
  
  # Command line mode
  python test_agent_server.py --query "What products do you offer?" --user-id "john" --token "abc123"
  
  # With custom server URL and session
  python test_agent_server.py --url "http://api.example.com:8000" --query "Hello" --user-id "alice" --token "xyz789" --session "session-123"
        """
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Query/question for the agent"
    )
    
    parser.add_argument(
        "-u", "--user-id",
        type=str,
        help="User ID"
    )
    
    parser.add_argument(
        "-t", "--token",
        type=str,
        help="Bearer token for authentication"
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:9010",
        help="Base URL of the API server (default: http://localhost:9010)"
    )
    
    parser.add_argument(
        "-s", "--session",
        type=str,
        help="Session ID for maintaining conversation context"
    )
    
    args = parser.parse_args()
    
    # If all required args provided, run in command-line mode
    if args.query and args.user_id and args.token:
        query_agent(
            query=args.query,
            user_id=args.user_id,
            bearer_token=args.token,
            base_url=args.url,
            session_id=args.session
        )
    else:
        # Otherwise, run in interactive mode
        if any([args.query, args.user_id, args.token]):
            print("✗ Error: When using command-line mode, you must provide --query, --user-id, and --token")
            print("   Run with -h for help")
            sys.exit(1)
        interactive_mode()


if __name__ == "__main__":
    main()