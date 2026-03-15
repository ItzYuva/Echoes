package com.echoes.api.model.dto;

import jakarta.validation.constraints.NotBlank;

public class QueryRequest {
    @NotBlank
    private String userId;
    @NotBlank
    private String decisionText;

    public QueryRequest() {
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getDecisionText() { return decisionText; }
    public void setDecisionText(String decisionText) { this.decisionText = decisionText; }
}
