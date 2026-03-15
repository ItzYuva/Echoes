package com.echoes.api.service;

import com.echoes.api.model.dto.DecisionRequest;
import com.echoes.api.model.dto.DecisionResponseDto;
import com.echoes.api.model.entity.Decision;
import com.echoes.api.repository.DecisionRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;

@Service
public class DecisionService {

    private final DecisionRepository decisionRepo;

    public DecisionService(DecisionRepository decisionRepo) {
        this.decisionRepo = decisionRepo;
    }

    public DecisionResponseDto logDecision(DecisionRequest req) {
        Instant now = Instant.now();
        Instant followUp = now.plus(180, ChronoUnit.DAYS); // 6 months

        Decision decision = Decision.builder()
                .userId(UUID.fromString(req.getUserId()))
                .queryId(req.getQueryId() != null ? UUID.fromString(req.getQueryId()) : null)
                .decisionText(req.getDecisionText())
                .decisionType(req.getDecisionType())
                .chosenPath(req.getChosenPath())
                .followUpAt(followUp)
                .build();

        decision = decisionRepo.save(decision);

        return DecisionResponseDto.builder()
                .decisionId(decision.getId().toString())
                .createdAt(decision.getCreatedAt().toString())
                .followUpScheduled(followUp.toString())
                .build();
    }

    public List<Decision> getUserDecisions(String userId) {
        return decisionRepo.findByUserIdOrderByCreatedAtDesc(UUID.fromString(userId));
    }
}
