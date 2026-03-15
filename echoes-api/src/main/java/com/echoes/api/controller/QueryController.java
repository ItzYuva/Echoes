package com.echoes.api.controller;

import com.echoes.api.exception.IntakeNotCompleteException;
import com.echoes.api.model.dto.QueryRequest;
import com.echoes.api.model.dto.QueryResponseDto;
import com.echoes.api.service.IntakeService;
import com.echoes.api.service.QueryService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/query")
public class QueryController {

    private final QueryService queryService;
    private final IntakeService intakeService;

    public QueryController(QueryService queryService, IntakeService intakeService) {
        this.queryService = queryService;
        this.intakeService = intakeService;
    }

    @PostMapping
    public ResponseEntity<QueryResponseDto> query(@Valid @RequestBody QueryRequest request,
                                                   Authentication auth) {
        String userId = (String) auth.getPrincipal();
        if (!intakeService.isIntakeComplete(userId)) {
            throw new IntakeNotCompleteException(userId);
        }
        QueryResponseDto response = queryService.query(userId, request.getDecisionText());
        return ResponseEntity.ok(response);
    }
}
