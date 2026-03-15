package com.echoes.api.model.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "decisions")
public class Decision {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Column(name = "query_id")
    private UUID queryId;

    @Column(name = "decision_text", nullable = false, columnDefinition = "TEXT")
    private String decisionText;

    @Column(name = "decision_type", length = 50)
    private String decisionType;

    @Column(name = "chosen_path")
    private String chosenPath;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "follow_up_at")
    private Instant followUpAt;

    @Column(name = "follow_up_sent")
    private boolean followUpSent = false;

    @Column(name = "reflection_received")
    private boolean reflectionReceived = false;

    @Column(name = "reflection_text", columnDefinition = "TEXT")
    private String reflectionText;

    @Column(name = "reflection_received_at")
    private Instant reflectionReceivedAt;

    public Decision() {
    }

    public Decision(UUID id, UUID userId, UUID queryId, String decisionText, String decisionType, String chosenPath,
                    Instant createdAt, Instant followUpAt, boolean followUpSent, boolean reflectionReceived,
                    String reflectionText, Instant reflectionReceivedAt) {
        this.id = id;
        this.userId = userId;
        this.queryId = queryId;
        this.decisionText = decisionText;
        this.decisionType = decisionType;
        this.chosenPath = chosenPath;
        this.createdAt = createdAt;
        this.followUpAt = followUpAt;
        this.followUpSent = followUpSent;
        this.reflectionReceived = reflectionReceived;
        this.reflectionText = reflectionText;
        this.reflectionReceivedAt = reflectionReceivedAt;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getUserId() { return userId; }
    public void setUserId(UUID userId) { this.userId = userId; }

    public UUID getQueryId() { return queryId; }
    public void setQueryId(UUID queryId) { this.queryId = queryId; }

    public String getDecisionText() { return decisionText; }
    public void setDecisionText(String decisionText) { this.decisionText = decisionText; }

    public String getDecisionType() { return decisionType; }
    public void setDecisionType(String decisionType) { this.decisionType = decisionType; }

    public String getChosenPath() { return chosenPath; }
    public void setChosenPath(String chosenPath) { this.chosenPath = chosenPath; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getFollowUpAt() { return followUpAt; }
    public void setFollowUpAt(Instant followUpAt) { this.followUpAt = followUpAt; }

    public boolean isFollowUpSent() { return followUpSent; }
    public void setFollowUpSent(boolean followUpSent) { this.followUpSent = followUpSent; }

    public boolean isReflectionReceived() { return reflectionReceived; }
    public void setReflectionReceived(boolean reflectionReceived) { this.reflectionReceived = reflectionReceived; }

    public String getReflectionText() { return reflectionText; }
    public void setReflectionText(String reflectionText) { this.reflectionText = reflectionText; }

    public Instant getReflectionReceivedAt() { return reflectionReceivedAt; }
    public void setReflectionReceivedAt(Instant reflectionReceivedAt) { this.reflectionReceivedAt = reflectionReceivedAt; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private UUID id;
        private UUID userId;
        private UUID queryId;
        private String decisionText;
        private String decisionType;
        private String chosenPath;
        private Instant createdAt;
        private Instant followUpAt;
        private boolean followUpSent = false;
        private boolean reflectionReceived = false;
        private String reflectionText;
        private Instant reflectionReceivedAt;

        public Builder id(UUID id) { this.id = id; return this; }
        public Builder userId(UUID userId) { this.userId = userId; return this; }
        public Builder queryId(UUID queryId) { this.queryId = queryId; return this; }
        public Builder decisionText(String decisionText) { this.decisionText = decisionText; return this; }
        public Builder decisionType(String decisionType) { this.decisionType = decisionType; return this; }
        public Builder chosenPath(String chosenPath) { this.chosenPath = chosenPath; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public Builder followUpAt(Instant followUpAt) { this.followUpAt = followUpAt; return this; }
        public Builder followUpSent(boolean followUpSent) { this.followUpSent = followUpSent; return this; }
        public Builder reflectionReceived(boolean reflectionReceived) { this.reflectionReceived = reflectionReceived; return this; }
        public Builder reflectionText(String reflectionText) { this.reflectionText = reflectionText; return this; }
        public Builder reflectionReceivedAt(Instant reflectionReceivedAt) { this.reflectionReceivedAt = reflectionReceivedAt; return this; }

        public Decision build() {
            Decision obj = new Decision();
            obj.id = this.id;
            obj.userId = this.userId;
            obj.queryId = this.queryId;
            obj.decisionText = this.decisionText;
            obj.decisionType = this.decisionType;
            obj.chosenPath = this.chosenPath;
            obj.createdAt = this.createdAt;
            obj.followUpAt = this.followUpAt;
            obj.followUpSent = this.followUpSent;
            obj.reflectionReceived = this.reflectionReceived;
            obj.reflectionText = this.reflectionText;
            obj.reflectionReceivedAt = this.reflectionReceivedAt;
            return obj;
        }
    }
}
