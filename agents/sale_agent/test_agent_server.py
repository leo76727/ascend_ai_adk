"""
Test script for FastAPI Sales Agent Server
Tests various endpoints and scenarios including authentication, sessions, and error handling.
"""

import requests
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime


class AgentServerTester:
    """Test client for the FastAPI Sales Agent Server"""
    
    def __init__(self, base_url: str = "http://localhost:9010", bearer_token: str = "test-token-12345"):
        self.base_url = base_url.rstrip('/')
        self.bearer_token = bearer_token
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
    
    def print_separator(self, title: str):
        """Print a formatted separator for test sections"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80 + "\n")
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        self.print_separator("Testing Health Check Endpoint")
        
        try:
            response = requests.get(f"{self.base_url}/health/")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                print("✓ Health check passed")
                return True
            else:
                print("✗ Health check failed")
                return False
        except Exception as e:
            print(f"✗ Health check error: {e}")
            return False
    
    def test_sales_agent(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        user_id: str = "test-user",
        use_auth: bool = True
    ) -> Optional[Dict[Any, Any]]:
        """Test the sales agent endpoint with a query"""
        
        print(f"\nQuery: {query}")
        print(f"Session ID: {session_id or 'New Session'}")
        print(f"User ID: {user_id}")
        print(f"Using Auth: {use_auth}")
        
        params = {
            "query": query,
            "user_id": user_id
        }
        
        if session_id:
            params["session_id"] = session_id
        
        headers = self.headers if use_auth else {}
        
        try:
            response = requests.get(
                f"{self.base_url}/sales-agent/",
                params=params,
                headers=headers
            )
            
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
                print("✓ Request successful")
                return result
            else:
                print(f"Response: {response.text}")
                print("✗ Request failed")
                return None
                
        except Exception as e:
            print(f"✗ Request error: {e}")
            return None
    
    def test_without_authentication(self):
        """Test endpoint without bearer token"""
        self.print_separator("Testing Without Authentication")
        self.test_sales_agent(
            query="Hello, I need help with sales",
            use_auth=False
        )
    
    def test_with_authentication(self):
        """Test endpoint with bearer token"""
        self.print_separator("Testing With Authentication")
        return self.test_sales_agent(
            query="What products do you offer?",
            use_auth=True
        )
    
    def test_session_continuity(self):
        """Test that session maintains context across requests"""
        self.print_separator("Testing Session Continuity")
        
        session_id = str(uuid.uuid4())
        user_id = "session-test-user"
        
        print("First request in session:")
        self.test_sales_agent(
            query="My name is Alice and I'm interested in your products",
            session_id=session_id,
            user_id=user_id
        )
        
        print("\n" + "-"*80)
        print("Second request in same session (should remember context):")
        self.test_sales_agent(
            query="What did I just tell you my name was?",
            session_id=session_id,
            user_id=user_id
        )
    
    def test_multiple_users(self):
        """Test multiple users with different sessions"""
        self.print_separator("Testing Multiple Users")
        
        users = ["user-1", "user-2", "user-3"]
        
        for user_id in users:
            print(f"\n--- Testing User: {user_id} ---")
            self.test_sales_agent(
                query=f"Hello, I'm {user_id}",
                user_id=user_id
            )
    
    def test_missing_parameters(self):
        """Test endpoint with missing required parameters"""
        self.print_separator("Testing Missing Parameters")
        
        try:
            response = requests.get(
                f"{self.base_url}/sales-agent/",
                headers=self.headers
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 422:
                print("✓ Correctly handled missing query parameter")
            else:
                print("✗ Unexpected response for missing parameters")
                
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def test_invalid_bearer_token(self):
        """Test with invalid bearer token"""
        self.print_separator("Testing Invalid Bearer Token")
        
        invalid_headers = {
            "Authorization": "Bearer invalid-token-xyz",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/sales-agent/",
                params={"query": "Test query"},
                headers=invalid_headers
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def test_long_query(self):
        """Test with a long, complex query"""
        self.print_separator("Testing Long Query")
        
        long_query = """
        I am looking for a comprehensive sales solution that can handle 
        multiple aspects of my business including inventory management, 
        customer relationship management, analytics, reporting, and 
        integration with existing systems. Can you provide detailed 
        information about your offerings and pricing?
        """
        
        self.test_sales_agent(query=long_query.strip())
    
    def run_all_tests(self):
        """Run all test scenarios"""
        print("\n")
        print("╔" + "═"*78 + "╗")
        print("║" + " "*20 + "SALES AGENT SERVER TEST SUITE" + " "*28 + "║")
        print("╚" + "═"*78 + "╝")
        print(f"\nTesting server at: {self.base_url}")
        print(f"Using bearer token: {self.bearer_token}")
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests
        self.test_health_check()
        self.test_without_authentication()
        self.test_with_authentication()
        self.test_session_continuity()
        self.test_multiple_users()
        self.test_missing_parameters()
        self.test_invalid_bearer_token()
        self.test_long_query()
        
        print("\n")
        print("╔" + "═"*78 + "╗")
        print("║" + " "*27 + "TESTS COMPLETED" + " "*35 + "║")
        print("╚" + "═"*78 + "╝")
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def main():
    """Main test execution"""
    # Configuration
    BASE_URL = "http://localhost:9010"  # Change if server runs on different port
    BEARER_TOKEN = "test-token-12345"   # Change to match your token requirements
    
    # Initialize tester
    tester = AgentServerTester(base_url=BASE_URL, bearer_token=BEARER_TOKEN)
    
    # Run all tests
    tester.run_all_tests()
    
    # Or run individual tests:
    # tester.test_health_check()
    # tester.test_with_authentication()
    # tester.test_session_continuity()


if __name__ == "__main__":
    main()