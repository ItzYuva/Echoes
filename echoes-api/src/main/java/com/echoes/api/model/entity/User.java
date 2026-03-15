package com.echoes.api.model.entity;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "auth_token_hash", nullable = false)
    private String authTokenHash;

    @Column(name = "intake_completed")
    private boolean intakeCompleted = false;

    @Column(name = "values_vector_json", columnDefinition = "TEXT")
    private String valuesVectorJson;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "last_active_at", nullable = false)
    private Instant lastActiveAt;

    public User() {
    }

    public User(UUID id, String authTokenHash, boolean intakeCompleted, Instant createdAt, Instant lastActiveAt) {
        this.id = id;
        this.authTokenHash = authTokenHash;
        this.intakeCompleted = intakeCompleted;
        this.createdAt = createdAt;
        this.lastActiveAt = lastActiveAt;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getAuthTokenHash() {
        return authTokenHash;
    }

    public void setAuthTokenHash(String authTokenHash) {
        this.authTokenHash = authTokenHash;
    }

    public boolean isIntakeCompleted() {
        return intakeCompleted;
    }

    public void setIntakeCompleted(boolean intakeCompleted) {
        this.intakeCompleted = intakeCompleted;
    }

    public String getValuesVectorJson() {
        return valuesVectorJson;
    }

    public void setValuesVectorJson(String valuesVectorJson) {
        this.valuesVectorJson = valuesVectorJson;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getLastActiveAt() {
        return lastActiveAt;
    }

    public void setLastActiveAt(Instant lastActiveAt) {
        this.lastActiveAt = lastActiveAt;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private UUID id;
        private String authTokenHash;
        private boolean intakeCompleted = false;
        private Instant createdAt;
        private Instant lastActiveAt;

        public Builder id(UUID id) { this.id = id; return this; }
        public Builder authTokenHash(String authTokenHash) { this.authTokenHash = authTokenHash; return this; }
        public Builder intakeCompleted(boolean intakeCompleted) { this.intakeCompleted = intakeCompleted; return this; }
        public Builder createdAt(Instant createdAt) { this.createdAt = createdAt; return this; }
        public Builder lastActiveAt(Instant lastActiveAt) { this.lastActiveAt = lastActiveAt; return this; }

        public User build() {
            User obj = new User();
            obj.id = this.id;
            obj.authTokenHash = this.authTokenHash;
            obj.intakeCompleted = this.intakeCompleted;
            obj.createdAt = this.createdAt;
            obj.lastActiveAt = this.lastActiveAt;
            return obj;
        }
    }
}
