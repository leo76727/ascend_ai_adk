package com.google.adk.client;

/**
 * Represents a web user interacting with the agent.
 */
public class WebUser {
    private String userId;
    private String userName;
    private String sessionId;
    private String authToken;

    public WebUser() {
    }

    public WebUser(String userId, String userName, String sessionId, String authToken) {
        this.userId = userId;
        this.userName = userName;
        this.sessionId = sessionId;
        this.authToken = authToken;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getUserName() {
        return userName;
    }

    public void setUserName(String userName) {
        this.userName = userName;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }
    
    public String getAuthToken() {
        return authToken;
    }

    public void setAuthToken(String authToken) {
        this.authToken = authToken;
    }
}
