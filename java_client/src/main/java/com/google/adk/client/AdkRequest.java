package com.google.adk.client;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * Represents the request body sent to the agent's /run endpoint.
 * Structure matches Google ADK Agent Runner API.
 */
public class AdkRequest {
    private String appName;
    private String userId;
    private String sessionId;
    private NewMessage newMessage;

    public AdkRequest(String appName, String userId, String sessionId, String query) {
        this.appName = appName;
        this.userId = userId;
        this.sessionId = sessionId;
        this.newMessage = new NewMessage("user", Collections.singletonList(new Part(query)));
    }

    public String toJson() {
        // Simple manual JSON serialization to avoid dependencies like Jackson/Gson for this basic client
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"appName\":\"").append(escapeJson(appName)).append("\",");
        sb.append("\"userId\":\"").append(escapeJson(userId)).append("\",");
        if (sessionId != null) {
            sb.append("\"sessionId\":\"").append(escapeJson(sessionId)).append("\",");
        }
        sb.append("\"newMessage\":{");
        sb.append("\"role\":\"").append(newMessage.role).append("\",");
        sb.append("\"parts\":[");
        for (int i = 0; i < newMessage.parts.size(); i++) {
            Part part = newMessage.parts.get(i);
            sb.append("{\"text\":\"").append(escapeJson(part.text)).append("\"}");
            if (i < newMessage.parts.size() - 1) {
                sb.append(",");
            }
        }
        sb.append("]");
        sb.append("}");
        sb.append("}");
        return sb.toString();
    }

    private String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    // Inner classes for structure
    private static class NewMessage {
        String role;
        List<Part> parts;

        NewMessage(String role, List<Part> parts) {
            this.role = role;
            this.parts = parts;
        }
    }

    private static class Part {
        String text;

        Part(String text) {
            this.text = text;
        }
    }
}
