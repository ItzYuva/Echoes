package com.echoes.api.model.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class IntakeResponseDto {
    private String sessionId;
    private String message;
    private int turnNumber;
    @JsonProperty("isComplete")
    private boolean isComplete;
    private ValuesVectorDto valuesVector;

    public IntakeResponseDto() {
    }

    public IntakeResponseDto(String sessionId, String message, int turnNumber, boolean isComplete, ValuesVectorDto valuesVector) {
        this.sessionId = sessionId;
        this.message = message;
        this.turnNumber = turnNumber;
        this.isComplete = isComplete;
        this.valuesVector = valuesVector;
    }

    public String getSessionId() { return sessionId; }
    public void setSessionId(String sessionId) { this.sessionId = sessionId; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public int getTurnNumber() { return turnNumber; }
    public void setTurnNumber(int turnNumber) { this.turnNumber = turnNumber; }

    public boolean isComplete() { return isComplete; }
    public void setComplete(boolean isComplete) { this.isComplete = isComplete; }

    public ValuesVectorDto getValuesVector() { return valuesVector; }
    public void setValuesVector(ValuesVectorDto valuesVector) { this.valuesVector = valuesVector; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String sessionId;
        private String message;
        private int turnNumber;
        private boolean isComplete;
        private ValuesVectorDto valuesVector;

        public Builder sessionId(String sessionId) { this.sessionId = sessionId; return this; }
        public Builder message(String message) { this.message = message; return this; }
        public Builder turnNumber(int turnNumber) { this.turnNumber = turnNumber; return this; }
        public Builder isComplete(boolean isComplete) { this.isComplete = isComplete; return this; }
        public Builder valuesVector(ValuesVectorDto valuesVector) { this.valuesVector = valuesVector; return this; }

        public IntakeResponseDto build() {
            IntakeResponseDto obj = new IntakeResponseDto();
            obj.sessionId = this.sessionId;
            obj.message = this.message;
            obj.turnNumber = this.turnNumber;
            obj.isComplete = this.isComplete;
            obj.valuesVector = this.valuesVector;
            return obj;
        }
    }
}
