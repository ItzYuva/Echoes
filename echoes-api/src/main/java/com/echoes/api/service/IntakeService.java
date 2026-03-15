package com.echoes.api.service;

import com.echoes.api.exception.IntakeNotCompleteException;
import com.echoes.api.exception.ProfileNotFoundException;
import com.echoes.api.model.dto.IntakeResponseDto;
import com.echoes.api.model.dto.ValuesVectorDto;
import com.echoes.api.model.entity.IntakeSession;
import com.echoes.api.model.entity.User;
import com.echoes.api.repository.IntakeSessionRepository;
import com.echoes.api.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class IntakeService {

    private static final Logger log = LoggerFactory.getLogger(IntakeService.class);

    private final PythonBridgeService pythonBridge;
    private final IntakeSessionRepository sessionRepo;
    private final UserRepository userRepo;
    private final ObjectMapper objectMapper;

    public IntakeService(PythonBridgeService pythonBridge,
                         IntakeSessionRepository sessionRepo,
                         UserRepository userRepo,
                         ObjectMapper objectMapper) {
        this.pythonBridge = pythonBridge;
        this.sessionRepo = sessionRepo;
        this.userRepo = userRepo;
        this.objectMapper = objectMapper;
    }

    public IntakeResponseDto startIntake(String userId) {
        UUID userUuid = UUID.fromString(userId);

        // Create session
        IntakeSession session = IntakeSession.builder()
                .userId(userUuid)
                .build();
        session = sessionRepo.save(session);

        String sessionId = session.getId().toString();
        Map<String, Object> result = pythonBridge.startIntake(sessionId);

        return IntakeResponseDto.builder()
                .sessionId(sessionId)
                .message((String) result.get("message"))
                .turnNumber(toInt(result.get("turn_number")))
                .isComplete(false)
                .build();
    }

    @SuppressWarnings("unchecked")
    public IntakeResponseDto respond(String sessionId, String userId, String message) {
        UUID sessionUuid = UUID.fromString(sessionId);
        IntakeSession session = sessionRepo.findById(sessionUuid)
                .orElseThrow(() -> new RuntimeException("Session not found: " + sessionId));

        Map<String, Object> result = pythonBridge.intakeRespond(sessionId, message);

        boolean isComplete = Boolean.TRUE.equals(result.get("is_complete"));
        int turnNumber = toInt(result.get("turn_number"));

        session.setTurnCount(turnNumber);

        IntakeResponseDto.Builder response = IntakeResponseDto.builder()
                .sessionId(sessionId)
                .message((String) result.get("message"))
                .turnNumber(turnNumber)
                .isComplete(isComplete);

        if (isComplete) {
            session.setComplete(true);
            session.setCompletedAt(Instant.now());

            // Mark user as intake completed
            User user = userRepo.findById(UUID.fromString(userId))
                    .orElseThrow(() -> new ProfileNotFoundException(userId));
            user.setIntakeCompleted(true);

            // Extract values vector
            Map<String, Object> vv = (Map<String, Object>) result.get("values_vector");
            if (vv != null) {
                response.valuesVector(ValuesVectorDto.fromSnakeCaseMap(vv));

                // Store values vector JSON in the users table
                try {
                    user.setValuesVectorJson(objectMapper.writeValueAsString(vv));
                } catch (JsonProcessingException e) {
                    log.warn("Failed to serialize values vector: {}", e.getMessage());
                }
            }
            userRepo.save(user);

            log.info("Intake completed for user {} (session {})", userId, sessionId);
        }

        sessionRepo.save(session);
        return response.build();
    }

    public boolean isIntakeComplete(String userId) {
        return userRepo.findById(UUID.fromString(userId))
                .map(User::isIntakeCompleted)
                .orElse(false);
    }

    private static int toInt(Object val) {
        if (val instanceof Number n) return n.intValue();
        return 0;
    }
}
