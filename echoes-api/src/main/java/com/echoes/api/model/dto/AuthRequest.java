package com.echoes.api.model.dto;

public class AuthRequest {
    private String userId;
    private String token;

    public AuthRequest() {
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getToken() { return token; }
    public void setToken(String token) { this.token = token; }
}
