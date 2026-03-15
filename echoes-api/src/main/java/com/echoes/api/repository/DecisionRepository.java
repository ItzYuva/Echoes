package com.echoes.api.repository;

import com.echoes.api.model.entity.Decision;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface DecisionRepository extends JpaRepository<Decision, UUID> {
    List<Decision> findByUserIdOrderByCreatedAtDesc(UUID userId);
}
