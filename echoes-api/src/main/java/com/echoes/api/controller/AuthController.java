package com.echoes.api.controller;

import com.echoes.api.model.dto.AuthRequest;
import com.echoes.api.model.dto.AuthResponse;
import com.echoes.api.service.AuthService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/register")
    public ResponseEntity<AuthResponse> register() {
        AuthService.AuthResult result = authService.register();
        return ResponseEntity.status(HttpStatus.CREATED).body(
                AuthResponse.builder()
                        .userId(result.userId())
                        .token(result.token())
                        .intakeCompleted(result.intakeCompleted())
                        .build()
        );
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@RequestBody AuthRequest request) {
        AuthService.AuthResult result = authService.login(request.getUserId(), request.getToken());
        if (result == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        return ResponseEntity.ok(
                AuthResponse.builder()
                        .userId(result.userId())
                        .token(result.token())
                        .intakeCompleted(result.intakeCompleted())
                        .build()
        );
    }
}
