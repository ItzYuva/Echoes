package com.echoes.api.exception;

public class ProfileNotFoundException extends RuntimeException {
    public ProfileNotFoundException(String userId) {
        super("Profile not found for user: " + userId);
    }
}
