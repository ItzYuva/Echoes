package com.echoes.api.model.dto;

public class DecisionResponseDto {
    private String decisionId;
    private String createdAt;
    private String followUpScheduled;

    public DecisionResponseDto() {
    }

    public DecisionResponseDto(String decisionId, String createdAt, String followUpScheduled) {
        this.decisionId = decisionId;
        this.createdAt = createdAt;
        this.followUpScheduled = followUpScheduled;
    }

    public String getDecisionId() { return decisionId; }
    public void setDecisionId(String decisionId) { this.decisionId = decisionId; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public String getFollowUpScheduled() { return followUpScheduled; }
    public void setFollowUpScheduled(String followUpScheduled) { this.followUpScheduled = followUpScheduled; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String decisionId;
        private String createdAt;
        private String followUpScheduled;

        public Builder decisionId(String decisionId) { this.decisionId = decisionId; return this; }
        public Builder createdAt(String createdAt) { this.createdAt = createdAt; return this; }
        public Builder followUpScheduled(String followUpScheduled) { this.followUpScheduled = followUpScheduled; return this; }

        public DecisionResponseDto build() {
            DecisionResponseDto obj = new DecisionResponseDto();
            obj.decisionId = this.decisionId;
            obj.createdAt = this.createdAt;
            obj.followUpScheduled = this.followUpScheduled;
            return obj;
        }
    }
}
