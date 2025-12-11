package com.google.adk.client;

public class ClientTest {
    public static void main(String[] args) {
        try {
            // Setup
            String baseUrl = "http://localhost:8000";
            String appName = "trader_manager_agent";
            TraderAgentClient client = new TraderAgentClient(baseUrl, appName);

            // User Info
            WebUser user = new WebUser("user123", "Alice", null, "my-secret-token");

            // Query
            System.out.println("Sending query...");
            String response = client.queryAgent("What is the price of GOOG?", user);

            System.out.println("Response received:");
            System.out.println(response);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
