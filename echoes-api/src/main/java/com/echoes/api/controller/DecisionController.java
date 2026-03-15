package com.echoes.api.controller;

import com.echoes.api.model.dto.DecisionRequest;
import com.echoes.api.model.dto.DecisionResponseDto;
import com.echoes.api.model.entity.Decision;
import com.echoes.api.service.DecisionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/decisions")
public class DecisionController {

    private final DecisionService decisionService;

    public DecisionController(DecisionService decisionService) {
        this.decisionService = decisionService;
    }

    @PostMapping
    public ResponseEntity<DecisionResponseDto> logDecision(@Valid @RequestBody DecisionRequest request,
                                                            Authentication auth) {
        DecisionResponseDto response = decisionService.logDecision(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/{userId}")
    public ResponseEntity<List<Decision>> getDecisions(@PathVariable String userId) {
        return ResponseEntity.ok(decisionService.getUserDecisions(userId));
    }
}
