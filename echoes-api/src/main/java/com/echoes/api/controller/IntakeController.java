package com.echoes.api.controller;

import com.echoes.api.model.dto.IntakeRespondRequest;
import com.echoes.api.model.dto.IntakeResponseDto;
import com.echoes.api.model.dto.IntakeStartRequest;
import com.echoes.api.service.IntakeService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/intake")
public class IntakeController {

    private final IntakeService intakeService;

    public IntakeController(IntakeService intakeService) {
        this.intakeService = intakeService;
    }

    @PostMapping("/start")
    public ResponseEntity<IntakeResponseDto> start(Authentication auth) {
        String userId = (String) auth.getPrincipal();
        IntakeResponseDto response = intakeService.startIntake(userId);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/respond")
    public ResponseEntity<IntakeResponseDto> respond(@Valid @RequestBody IntakeRespondRequest request,
                                                     Authentication auth) {
        String userId = (String) auth.getPrincipal();
        IntakeResponseDto response = intakeService.respond(
                request.getSessionId(), userId, request.getMessage());
        return ResponseEntity.ok(response);
    }

    @GetMapping("/status/{userId}")
    public ResponseEntity<Map<String, Boolean>> status(@PathVariable String userId) {
        boolean complete = intakeService.isIntakeComplete(userId);
        return ResponseEntity.ok(Map.of("intakeCompleted", complete));
    }
}
