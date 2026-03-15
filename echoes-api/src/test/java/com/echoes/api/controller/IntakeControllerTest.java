package com.echoes.api.controller;

import com.echoes.api.service.AuthService;
import com.echoes.api.service.PythonBridgeService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class IntakeControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private AuthService authService;

    @MockitoBean
    private PythonBridgeService pythonBridge;

    @Test
    void start_shouldReturnFirstQuestion() throws Exception {
        AuthService.AuthResult user = authService.register();

        when(pythonBridge.startIntake(anyString())).thenReturn(Map.of(
                "session_id", "test-session",
                "message", "When you've regretted decisions in the past...",
                "turn_number", 0,
                "is_complete", false
        ));

        mockMvc.perform(post("/api/intake/start")
                        .header("Authorization", "Bearer " + user.token()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").isNotEmpty())
                .andExpect(jsonPath("$.complete").value(false));
    }

    @Test
    void status_shouldReturnIntakeStatus() throws Exception {
        AuthService.AuthResult user = authService.register();

        mockMvc.perform(get("/api/intake/status/" + user.userId())
                        .header("Authorization", "Bearer " + user.token()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.intakeCompleted").value(false));
    }

    @Test
    void start_withoutAuth_shouldReturn401() throws Exception {
        mockMvc.perform(post("/api/intake/start"))
                .andExpect(status().isUnauthorized());
    }
}
