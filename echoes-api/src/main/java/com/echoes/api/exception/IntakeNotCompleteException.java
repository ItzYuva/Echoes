package com.echoes.api.exception;

public class IntakeNotCompleteException extends RuntimeException {
    public IntakeNotCompleteException(String userId) {
        super("Intake not completed for user: " + userId);
    }
}
