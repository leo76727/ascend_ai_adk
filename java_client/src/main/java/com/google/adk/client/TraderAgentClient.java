package com.google.adk.client;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Client to interact with the Trader Agent ADK Runner.
 */
public class TraderAgentClient {

    private final String baseUrl;
    private final String appName;
    private final HttpClient httpClient;

    public TraderAgentClient(String baseUrl, String appName) {
        this.baseUrl = baseUrl;
        this.appName = appName;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    /**
     * Queries the trader agent.
     *
     * @param inquiry The natural language inquiry.
     * @param user    The web user making the request.
     * @return The response body from the agent (JSON string).
     * @throws IOException          If an I/O error occurs.
     * @throws InterruptedException If the operation is interrupted.
     * @throws RuntimeException     If the server returns a non-200 status.
     */
    public String queryAgent(String inquiry, WebUser user) throws IOException, InterruptedException {
        // 1. Prepare Request Data
        String finalSessionId = user.getSessionId() != null ? user.getSessionId() : "default-session-" + user.getUserId();
        AdkRequest adkRequest = new AdkRequest(this.appName, user.getUserId(), finalSessionId, inquiry);
        String requestBody = adkRequest.toJson();

        // 2. Prepare HTTP Request
        HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/run"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody));

        // Add Auth Token if present
        if (user.getAuthToken() != null && !user.getAuthToken().isEmpty()) {
            requestBuilder.header("Authorization", "Bearer " + user.getAuthToken());
        }

        HttpRequest request = requestBuilder.build();

        // 3. Send Request
        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            // 4. Handle Response
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                return response.body();
            } else {
                throw new RuntimeException("Agent query failed: HTTP " + response.statusCode() + " - " + response.body());
            }
        } catch (IOException | InterruptedException e) {
            // Log or rethrow as needed - here we rethrow to let caller handle
            throw e;
        }
    }
}
