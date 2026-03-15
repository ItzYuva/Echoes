package com.echoes.api.service;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class AuthServiceTest {

    @Autowired
    private AuthService authService;

    @Test
    void register_shouldCreateUserAndToken() {
        AuthService.AuthResult result = authService.register();
        assertNotNull(result.userId());
        assertNotNull(result.token());
        assertFalse(result.intakeCompleted());
    }

    @Test
    void validateToken_withValidToken_shouldReturnUserId() {
        AuthService.AuthResult result = authService.register();
        String userId = authService.validateToken(result.token());
        assertEquals(result.userId(), userId);
    }

    @Test
    void validateToken_withInvalidToken_shouldReturnNull() {
        String userId = authService.validateToken("invalid.token.here");
        assertNull(userId);
    }

    @Test
    void login_withValidCredentials_shouldSucceed() {
        AuthService.AuthResult registered = authService.register();
        AuthService.AuthResult loggedIn = authService.login(registered.userId(), registered.token());
        assertNotNull(loggedIn);
        assertEquals(registered.userId(), loggedIn.userId());
    }

    @Test
    void login_withWrongUserId_shouldFail() {
        AuthService.AuthResult registered = authService.register();
        AuthService.AuthResult result = authService.login("wrong-id", registered.token());
        assertNull(result);
    }
}
