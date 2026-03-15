package com.echoes.api.model.dto;

import jakarta.validation.constraints.NotBlank;

public class IntakeRespondRequest {
    @NotBlank
    private String sessionId;
    @NotBlank
    private String userId;
    @NotBlank
    private String message;

    public IntakeRespondRequest() {
    }

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
}
