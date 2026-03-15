package com.echoes.api.model.dto;

import jakarta.validation.constraints.NotBlank;

public class IntakeStartRequest {
    @NotBlank
    private String userId;

    public IntakeStartRequest() {
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
}
