package com.echoes.api.controller;

import com.echoes.api.service.AuthService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private AuthService authService;

    @Test
    void register_shouldReturnUserIdAndToken() throws Exception {
        mockMvc.perform(post("/api/auth/register"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.userId").isNotEmpty())
                .andExpect(jsonPath("$.token").isNotEmpty())
                .andExpect(jsonPath("$.intakeCompleted").value(false));
    }

    @Test
    void login_withValidCredentials_shouldSucceed() throws Exception {
        AuthService.AuthResult registered = authService.register();

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "%s", "token": "%s"}
                                """.formatted(registered.userId(), registered.token())))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(registered.userId()));
    }

    @Test
    void login_withInvalidToken_shouldReturn401() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "some-id", "token": "bad-token"}
                                """))
                .andExpect(status().isUnauthorized());
    }
}
