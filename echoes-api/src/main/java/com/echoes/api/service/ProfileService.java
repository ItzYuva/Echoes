package com.echoes.api.service;

import com.echoes.api.exception.ProfileNotFoundException;
import com.echoes.api.model.dto.ProfileResponseDto;
import com.echoes.api.model.dto.ValuesVectorDto;
import com.echoes.api.model.entity.User;
import com.echoes.api.repository.UserRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;

@Service
public class ProfileService {

    private static final Logger log = LoggerFactory.getLogger(ProfileService.class);

    private final UserRepository userRepo;
    private final ObjectMapper objectMapper;

    public ProfileService(UserRepository userRepo, ObjectMapper objectMapper) {
        this.userRepo = userRepo;
        this.objectMapper = objectMapper;
    }

    public ProfileResponseDto getProfile(String userId) {
        User user = userRepo.findById(UUID.fromString(userId))
                .orElseThrow(() -> new ProfileNotFoundException(userId));

        ValuesVectorDto vv = null;
        if (user.getValuesVectorJson() != null) {
            try {
                Map<String, Object> raw = objectMapper.readValue(
                        user.getValuesVectorJson(), new TypeReference<>() {});
                vv = ValuesVectorDto.fromSnakeCaseMap(raw);
            } catch (Exception e) {
                log.warn("Failed to parse values vector for user {}: {}", userId, e.getMessage());
            }
        }

        return ProfileResponseDto.builder()
                .userId(userId)
                .valuesVector(vv)
                .intakeVersion(1)
                .intakeTurns(0)
                .intakeDurationSeconds(0)
                .profileVersion(1)
                .createdAt(user.getCreatedAt() != null ? user.getCreatedAt().toString() : null)
                .updatedAt(user.getLastActiveAt() != null ? user.getLastActiveAt().toString() : null)
                .build();
    }

    public void updateProfile(String userId, ValuesVectorDto newValues) {
        User user = userRepo.findById(UUID.fromString(userId))
                .orElseThrow(() -> new ProfileNotFoundException(userId));

        try {
            user.setValuesVectorJson(objectMapper.writeValueAsString(newValues.toSnakeCaseMap()));
            userRepo.save(user);
        } catch (Exception e) {
            log.error("Failed to save values vector for user {}: {}", userId, e.getMessage());
        }
    }
}
