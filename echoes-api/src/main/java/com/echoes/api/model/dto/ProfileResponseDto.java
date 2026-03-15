package com.echoes.api.model.dto;

public class ProfileResponseDto {
    private String userId;
    private ValuesVectorDto valuesVector;
    private int intakeVersion;
    private int intakeTurns;
    private int intakeDurationSeconds;
    private int profileVersion;
    private String createdAt;
    private String updatedAt;

    public ProfileResponseDto() {
    }

    public ProfileResponseDto(String userId, ValuesVectorDto valuesVector, int intakeVersion, int intakeTurns,
                               int intakeDurationSeconds, int profileVersion, String createdAt, String updatedAt) {
        this.userId = userId;
        this.valuesVector = valuesVector;
        this.intakeVersion = intakeVersion;
        this.intakeTurns = intakeTurns;
        this.intakeDurationSeconds = intakeDurationSeconds;
        this.profileVersion = profileVersion;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }

    public ValuesVectorDto getValuesVector() { return valuesVector; }
    public void setValuesVector(ValuesVectorDto valuesVector) { this.valuesVector = valuesVector; }

    public int getIntakeVersion() { return intakeVersion; }
    public void setIntakeVersion(int intakeVersion) { this.intakeVersion = intakeVersion; }

    public int getIntakeTurns() { return intakeTurns; }
    public void setIntakeTurns(int intakeTurns) { this.intakeTurns = intakeTurns; }

    public int getIntakeDurationSeconds() { return intakeDurationSeconds; }
    public void setIntakeDurationSeconds(int intakeDurationSeconds) { this.intakeDurationSeconds = intakeDurationSeconds; }

    public int getProfileVersion() { return profileVersion; }
    public void setProfileVersion(int profileVersion) { this.profileVersion = profileVersion; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String userId;
        private ValuesVectorDto valuesVector;
        private int intakeVersion;
        private int intakeTurns;
        private int intakeDurationSeconds;
        private int profileVersion;
        private String createdAt;
        private String updatedAt;

        public Builder userId(String userId) { this.userId = userId; return this; }
        public Builder valuesVector(ValuesVectorDto valuesVector) { this.valuesVector = valuesVector; return this; }
        public Builder intakeVersion(int intakeVersion) { this.intakeVersion = intakeVersion; return this; }
        public Builder intakeTurns(int intakeTurns) { this.intakeTurns = intakeTurns; return this; }
        public Builder intakeDurationSeconds(int intakeDurationSeconds) { this.intakeDurationSeconds = intakeDurationSeconds; return this; }
        public Builder profileVersion(int profileVersion) { this.profileVersion = profileVersion; return this; }
        public Builder createdAt(String createdAt) { this.createdAt = createdAt; return this; }
        public Builder updatedAt(String updatedAt) { this.updatedAt = updatedAt; return this; }

        public ProfileResponseDto build() {
            ProfileResponseDto obj = new ProfileResponseDto();
            obj.userId = this.userId;
            obj.valuesVector = this.valuesVector;
            obj.intakeVersion = this.intakeVersion;
            obj.intakeTurns = this.intakeTurns;
            obj.intakeDurationSeconds = this.intakeDurationSeconds;
            obj.profileVersion = this.profileVersion;
            obj.createdAt = this.createdAt;
            obj.updatedAt = this.updatedAt;
            return obj;
        }
    }
}
