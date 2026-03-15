package com.echoes.api.service;

import com.echoes.api.exception.ProfileNotFoundException;
import com.echoes.api.model.dto.QueryResponseDto;
import com.echoes.api.model.dto.QueryResponseDto.*;
import com.echoes.api.model.dto.ValuesVectorDto;
import com.echoes.api.model.entity.User;
import com.echoes.api.repository.UserRepository;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class QueryService {

    private static final Logger log = LoggerFactory.getLogger(QueryService.class);

    private final PythonBridgeService pythonBridge;
    private final UserRepository userRepo;
    private final ObjectMapper objectMapper;

    public QueryService(PythonBridgeService pythonBridge, UserRepository userRepo, ObjectMapper objectMapper) {
        this.pythonBridge = pythonBridge;
        this.userRepo = userRepo;
        this.objectMapper = objectMapper;
    }

    @SuppressWarnings("unchecked")
    public QueryResponseDto query(String userId, String decisionText) {
        // Get user's values vector from Spring Boot's users table
        User user = userRepo.findById(UUID.fromString(userId))
                .orElseThrow(() -> new ProfileNotFoundException(userId));

        Map<String, Double> vvMap;
        try {
            Map<String, Object> raw = objectMapper.readValue(
                    user.getValuesVectorJson(), new TypeReference<>() {});
            ValuesVectorDto vv = ValuesVectorDto.fromSnakeCaseMap(raw);
            vvMap = vv.toSnakeCaseMap();
        } catch (Exception e) {
            log.error("Failed to parse values vector for user {}: {}", userId, e.getMessage());
            // Use neutral defaults
            vvMap = Map.of(
                "risk_tolerance", 0.5, "change_orientation", 0.5,
                "security_vs_growth", 0.5, "action_bias", 0.5,
                "social_weight", 0.5, "time_horizon", 0.5,
                "loss_sensitivity", 0.5, "ambiguity_tolerance", 0.5
            );
        }

        // Call Python RAG pipeline
        Map<String, Object> result = pythonBridge.query(userId, decisionText, vvMap);

        return mapToQueryResponse(result);
    }

    @SuppressWarnings("unchecked")
    private QueryResponseDto mapToQueryResponse(Map<String, Object> result) {
        Map<String, Object> pres = (Map<String, Object>) result.get("presentation");
        Map<String, Object> conf = (Map<String, Object>) result.get("confidence");
        Map<String, Object> qa = (Map<String, Object>) result.get("query_analysis");
        List<Map<String, Object>> storiesList = (List<Map<String, Object>>) result.get("stories");
        Map<String, Object> meta = (Map<String, Object>) result.get("metadata");

        // Presentation
        PresentationDto presentation = PresentationDto.builder()
                .text((String) pres.get("text"))
                .storiesCount(toInt(pres.get("stories_count")))
                .build();

        // Confidence
        ConfidenceDto confidence = ConfidenceDto.builder()
                .score(toDouble(conf.get("score")))
                .level((String) conf.get("level"))
                .reasons((List<String>) conf.get("reasons"))
                .build();

        // Query analysis
        QueryAnalysisDto queryAnalysis = QueryAnalysisDto.builder()
                .decisionType((String) qa.get("decision_type"))
                .decisionSubcategory((String) qa.get("decision_subcategory"))
                .coreTension((String) qa.get("core_tension"))
                .emotionalState((List<String>) qa.get("emotional_state"))
                .stakes((String) qa.get("stakes"))
                .keyFactors((List<String>) qa.get("key_factors"))
                .whatWouldHelp((String) qa.get("what_would_help"))
                .build();

        // Stories
        List<StoryDto> stories = new ArrayList<>();
        if (storiesList != null) {
            for (Map<String, Object> s : storiesList) {
                stories.add(StoryDto.builder()
                        .id((String) s.get("id"))
                        .decisionType((String) s.get("decision_type"))
                        .decisionSubcategory((String) s.get("decision_subcategory"))
                        .outcomeSentiment((String) s.get("outcome_sentiment"))
                        .timeElapsedMonths(toInt(s.get("time_elapsed_months")))
                        .emotionalRichness(toInt(s.get("emotional_richness")))
                        .keyThemes((List<String>) s.get("key_themes"))
                        .hindsightInsight((String) s.get("hindsight_insight"))
                        .isCounterNarrative(Boolean.TRUE.equals(s.get("is_counter_narrative")))
                        .compositeScore(toDouble(s.get("composite_score")))
                        .build());
            }
        }

        // Metadata
        MetadataDto metadata = MetadataDto.builder()
                .totalLatencyMs(toInt(meta.get("total_latency_ms")))
                .liveSearchUsed(Boolean.TRUE.equals(meta.get("live_search_used")))
                .agentSearching(Boolean.TRUE.equals(meta.get("agent_searching")))
                .candidatesFound(toInt(meta.get("candidates_found")))
                .storiesPresented(toInt(meta.get("stories_presented")))
                .counterNarrativeRatio(toDouble(meta.get("counter_narrative_ratio")))
                .build();

        return QueryResponseDto.builder()
                .queryId(UUID.randomUUID().toString())
                .presentation(presentation)
                .confidence(confidence)
                .queryAnalysis(queryAnalysis)
                .stories(stories)
                .metadata(metadata)
                .build();
    }

    private static int toInt(Object val) {
        if (val instanceof Number n) return n.intValue();
        return 0;
    }

    private static double toDouble(Object val) {
        if (val instanceof Number n) return n.doubleValue();
        return 0.0;
    }
}
