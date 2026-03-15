package com.echoes.api.controller;

import com.echoes.api.model.entity.User;
import com.echoes.api.repository.UserRepository;
import com.echoes.api.service.AuthService;
import com.echoes.api.service.PythonBridgeService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.UUID;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class QueryControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private AuthService authService;

    @Autowired
    private UserRepository userRepository;

    @MockitoBean
    private PythonBridgeService pythonBridge;

    @Test
    void query_withoutIntakeComplete_shouldReturn403() throws Exception {
        AuthService.AuthResult user = authService.register();

        mockMvc.perform(post("/api/query")
                        .header("Authorization", "Bearer " + user.token())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "%s", "decisionText": "Should I leave my job?"}
                                """.formatted(user.userId())))
                .andExpect(status().isForbidden());
    }

    @Test
    void query_withoutAuth_shouldReturn401() throws Exception {
        mockMvc.perform(post("/api/query")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"userId": "some-id", "decisionText": "Should I leave my job?"}
                                """))
                .andExpect(status().isUnauthorized());
    }
}
