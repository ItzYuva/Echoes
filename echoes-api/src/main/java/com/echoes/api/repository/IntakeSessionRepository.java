package com.echoes.api.repository;

import com.echoes.api.model.entity.IntakeSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface IntakeSessionRepository extends JpaRepository<IntakeSession, UUID> {
    Optional<IntakeSession> findByUserIdAndIsCompleteFalse(UUID userId);
}
