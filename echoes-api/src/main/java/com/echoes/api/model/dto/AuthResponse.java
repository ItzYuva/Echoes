package com.echoes.api.model.dto;

public class AuthResponse {
    private String userId;
    private String token;
    private boolean intakeCompleted;

    public AuthResponse() {
    }

    public AuthResponse(String userId, String token, boolean intakeCompleted) {
        this.userId = userId;
        this.token = token;
        this.intakeCompleted = intakeCompleted;
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getToken() { return token; }
    public void setToken(String token) { this.token = token; }

    public boolean isIntakeCompleted() { return intakeCompleted; }
    public void setIntakeCompleted(boolean intakeCompleted) { this.intakeCompleted = intakeCompleted; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String userId;
        private String token;
        private boolean intakeCompleted;

        public Builder userId(String userId) { this.userId = userId; return this; }
        public Builder token(String token) { this.token = token; return this; }
        public Builder intakeCompleted(boolean intakeCompleted) { this.intakeCompleted = intakeCompleted; return this; }

        public AuthResponse build() {
            AuthResponse obj = new AuthResponse();
            obj.userId = this.userId;
            obj.token = this.token;
            obj.intakeCompleted = this.intakeCompleted;
            return obj;
        }
    }
}
