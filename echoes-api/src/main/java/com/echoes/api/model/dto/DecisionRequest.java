package com.echoes.api.model.dto;

import jakarta.validation.constraints.NotBlank;

public class DecisionRequest {
    @NotBlank
    private String userId;
    private String queryId;
    @NotBlank
    private String decisionText;
    private String decisionType;
    private String chosenPath;

    public DecisionRequest() {
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public String getQueryId() { return queryId; }
    public void setQueryId(String queryId) { this.queryId = queryId; }

    public String getDecisionText() { return decisionText; }
    public void setDecisionText(String decisionText) { this.decisionText = decisionText; }

    public String getDecisionType() { return decisionType; }
    public void setDecisionType(String decisionType) { this.decisionType = decisionType; }

    public String getChosenPath() { return chosenPath; }
    public void setChosenPath(String chosenPath) { this.chosenPath = chosenPath; }
}
