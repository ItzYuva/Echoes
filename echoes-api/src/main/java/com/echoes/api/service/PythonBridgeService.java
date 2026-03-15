package com.echoes.api.service;

import com.echoes.api.config.PythonApiConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.Map;

@Service
public class PythonBridgeService {

    private static final Logger log = LoggerFactory.getLogger(PythonBridgeService.class);

    private final WebClient webClient;
    private final Duration timeout;

    public PythonBridgeService(PythonApiConfig config) {
        this.webClient = WebClient.builder()
                .baseUrl(config.getBaseUrl())
                .codecs(c -> c.defaultCodecs().maxInMemorySize(10 * 1024 * 1024)) // 10MB
                .build();
        this.timeout = Duration.ofSeconds(config.getTimeoutSeconds());
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> startIntake(String sessionId) {
        return webClient.post()
                .uri("/internal/intake/start")
                .bodyValue(Map.of("session_id", sessionId))
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> intakeRespond(String sessionId, String message) {
        return webClient.post()
                .uri("/internal/intake/respond")
                .bodyValue(Map.of("session_id", sessionId, "message", message))
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> query(String userId, String decisionText, Map<String, Double> valuesVector) {
        return webClient.post()
                .uri("/internal/query")
                .bodyValue(Map.of(
                        "user_id", userId != null ? userId : "",
                        "decision_text", decisionText,
                        "values_vector", valuesVector
                ))
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getProfile(String userId) {
        return webClient.get()
                .uri("/internal/profile/{userId}", userId)
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> createProfile(Map<String, Object> body) {
        return webClient.post()
                .uri("/internal/profile")
                .bodyValue(body)
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> updateProfile(String userId, Map<String, Object> body) {
        return webClient.put()
                .uri("/internal/profile/{userId}", userId)
                .bodyValue(body)
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getProfileHistory(String userId) {
        return webClient.get()
                .uri("/internal/profile/{userId}/history", userId)
                .retrieve()
                .bodyToMono(Map.class)
                .timeout(timeout)
                .block();
    }

    public boolean healthCheck() {
        try {
            webClient.get()
                    .uri("/internal/health")
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(Duration.ofSeconds(5))
                    .block();
            return true;
        } catch (Exception e) {
            log.warn("Python API health check failed: {}", e.getMessage());
            return false;
        }
    }
}
