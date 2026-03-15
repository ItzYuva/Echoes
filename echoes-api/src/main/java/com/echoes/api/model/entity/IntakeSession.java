package com.echoes.api.model.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "intake_sessions")
public class IntakeSession {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Column(name = "is_complete")
    private boolean isComplete = false;

    @Column(name = "turn_count")
    private int turnCount = 0;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    public IntakeSession() {
    }

    public IntakeSession(UUID id, UUID userId, boolean isComplete, int turnCount, Instant createdAt, Instant completedAt) {
        this.id = id;
        this.userId = userId;
        this.isComplete = isComplete;
        this.turnCount = turnCount;
        this.createdAt = createdAt;
        this.completedAt = completedAt;
    }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getUserId() { return userId; }
    public void setUserId(UUID userId) { this.userId = userId; }

    public boolean isComplete() { return isComplete; }
    public void setComplete(boolean isComplete) { this.isComplete = isComplete; }

    public int getTurnCount() { return turnCount; }
    public void setTurnCount(int turnCount) { this.turnCount = turnCount; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private UUID id;
        private UUID userId;
        private boolean isComplete = false;
        private int turnCount = 0;
        private Instant createdAt;
        private Instant completedAt;

        public Builder id(UUID id) { this.id = id; return this; }
        public Builder userId(UUID userId) { this.userId = userId; return this; }
        public Builder isComplete(boolean isComplete) { this.isComplete = isComplete; return this; }
        public Builder turnCount(int turnCount) { this.turnCount = turnCount; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public Builder completedAt(Instant completedAt) { this.completedAt = completedAt; return this; }

        public IntakeSession build() {
            IntakeSession obj = new IntakeSession();
            obj.id = this.id;
            obj.userId = this.userId;
            obj.isComplete = this.isComplete;
            obj.turnCount = this.turnCount;
            obj.createdAt = this.createdAt;
            obj.completedAt = this.completedAt;
            return obj;
        }
    }
}
