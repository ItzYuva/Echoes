package com.echoes.api.model.dto;

import java.util.List;
import java.util.Map;

public class QueryResponseDto {
    private String queryId;
    private PresentationDto presentation;
    private ConfidenceDto confidence;
    private QueryAnalysisDto queryAnalysis;
    private List<StoryDto> stories;
    private MetadataDto metadata;

    public QueryResponseDto() {
    }

    public QueryResponseDto(String queryId, PresentationDto presentation, ConfidenceDto confidence,
                            QueryAnalysisDto queryAnalysis, List<StoryDto> stories, MetadataDto metadata) {
        this.queryId = queryId;
        this.presentation = presentation;
        this.confidence = confidence;
        this.queryAnalysis = queryAnalysis;
        this.stories = stories;
        this.metadata = metadata;
    }

    public String getQueryId() { return queryId; }
    public void setQueryId(String queryId) { this.queryId = queryId; }

    public PresentationDto getPresentation() { return presentation; }
    public void setPresentation(PresentationDto presentation) { this.presentation = presentation; }

    public ConfidenceDto getConfidence() { return confidence; }
    public void setConfidence(ConfidenceDto confidence) { this.confidence = confidence; }

    public QueryAnalysisDto getQueryAnalysis() { return queryAnalysis; }
    public void setQueryAnalysis(QueryAnalysisDto queryAnalysis) { this.queryAnalysis = queryAnalysis; }

    public List<StoryDto> getStories() { return stories; }
    public void setStories(List<StoryDto> stories) { this.stories = stories; }

    public MetadataDto getMetadata() { return metadata; }
    public void setMetadata(MetadataDto metadata) { this.metadata = metadata; }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String queryId;
        private PresentationDto presentation;
        private ConfidenceDto confidence;
        private QueryAnalysisDto queryAnalysis;
        private List<StoryDto> stories;
        private MetadataDto metadata;

        public Builder queryId(String queryId) { this.queryId = queryId; return this; }
        public Builder presentation(PresentationDto presentation) { this.presentation = presentation; return this; }
        public Builder confidence(ConfidenceDto confidence) { this.confidence = confidence; return this; }
        public Builder queryAnalysis(QueryAnalysisDto queryAnalysis) { this.queryAnalysis = queryAnalysis; return this; }
        public Builder stories(List<StoryDto> stories) { this.stories = stories; return this; }
        public Builder metadata(MetadataDto metadata) { this.metadata = metadata; return this; }

        public QueryResponseDto build() {
            QueryResponseDto obj = new QueryResponseDto();
            obj.queryId = this.queryId;
            obj.presentation = this.presentation;
            obj.confidence = this.confidence;
            obj.queryAnalysis = this.queryAnalysis;
            obj.stories = this.stories;
            obj.metadata = this.metadata;
            return obj;
        }
    }

    public static class PresentationDto {
        private String text;
        private int storiesCount;

        public PresentationDto() {
        }

        public PresentationDto(String text, int storiesCount) {
            this.text = text;
            this.storiesCount = storiesCount;
        }

        public String getText() { return text; }
        public void setText(String text) { this.text = text; }

        public int getStoriesCount() { return storiesCount; }
        public void setStoriesCount(int storiesCount) { this.storiesCount = storiesCount; }

        public static Builder builder() {
            return new Builder();
        }

        public static class Builder {
            private String text;
            private int storiesCount;

            public Builder text(String text) { this.text = text; return this; }
            public Builder storiesCount(int storiesCount) { this.storiesCount = storiesCount; return this; }

            public PresentationDto build() {
                PresentationDto obj = new PresentationDto();
                obj.text = this.text;
                obj.storiesCount = this.storiesCount;
                return obj;
            }
        }
    }

    public static class ConfidenceDto {
        private double score;
        private String level;
        private List<String> reasons;

        public ConfidenceDto() {
        }

        public ConfidenceDto(double score, String level, List<String> reasons) {
            this.score = score;
            this.level = level;
            this.reasons = reasons;
        }

        public double getScore() { return score; }
        public void setScore(double score) { this.score = score; }

        public String getLevel() { return level; }
        public void setLevel(String level) { this.level = level; }

        public List<String> getReasons() { return reasons; }
        public void setReasons(List<String> reasons) { this.reasons = reasons; }

        public static Builder builder() {
            return new Builder();
        }

        public static class Builder {
            private double score;
            private String level;
            private List<String> reasons;

            public Builder score(double score) { this.score = score; return this; }
            public Builder level(String level) { this.level = level; return this; }
            public Builder reasons(List<String> reasons) { this.reasons = reasons; return this; }

            public ConfidenceDto build() {
                ConfidenceDto obj = new ConfidenceDto();
                obj.score = this.score;
                obj.level = this.level;
                obj.reasons = this.reasons;
                return obj;
            }
        }
    }

    public static class QueryAnalysisDto {
        private String decisionType;
        private String decisionSubcategory;
        private String coreTension;
        private List<String> emotionalState;
        private String stakes;
        private List<String> keyFactors;
        private String whatWouldHelp;

        public QueryAnalysisDto() {
        }

        public QueryAnalysisDto(String decisionType, String decisionSubcategory, String coreTension,
                                List<String> emotionalState, String stakes, List<String> keyFactors, String whatWouldHelp) {
            this.decisionType = decisionType;
            this.decisionSubcategory = decisionSubcategory;
            this.coreTension = coreTension;
            this.emotionalState = emotionalState;
            this.stakes = stakes;
            this.keyFactors = keyFactors;
            this.whatWouldHelp = whatWouldHelp;
        }

        public String getDecisionType() { return decisionType; }
        public void setDecisionType(String decisionType) { this.decisionType = decisionType; }

        public String getDecisionSubcategory() { return decisionSubcategory; }
        public void setDecisionSubcategory(String decisionSubcategory) { this.decisionSubcategory = decisionSubcategory; }

        public String getCoreTension() { return coreTension; }
        public void setCoreTension(String coreTension) { this.coreTension = coreTension; }

        public List<String> getEmotionalState() { return emotionalState; }
        public void setEmotionalState(List<String> emotionalState) { this.emotionalState = emotionalState; }

        public String getStakes() { return stakes; }
        public void setStakes(String stakes) { this.stakes = stakes; }

        public List<String> getKeyFactors() { return keyFactors; }
        public void setKeyFactors(List<String> keyFactors) { this.keyFactors = keyFactors; }

        public String getWhatWouldHelp() { return whatWouldHelp; }
        public void setWhatWouldHelp(String whatWouldHelp) { this.whatWouldHelp = whatWouldHelp; }

        public static Builder builder() {
            return new Builder();
        }

        public static class Builder {
            private String decisionType;
            private String decisionSubcategory;
            private String coreTension;
            private List<String> emotionalState;
            private String stakes;
            private List<String> keyFactors;
            private String whatWouldHelp;

            public Builder decisionType(String decisionType) { this.decisionType = decisionType; return this; }
            public Builder decisionSubcategory(String decisionSubcategory) { this.decisionSubcategory = decisionSubcategory; return this; }
            public Builder coreTension(String coreTension) { this.coreTension = coreTension; return this; }
            public Builder emotionalState(List<String> emotionalState) { this.emotionalState = emotionalState; return this; }
            public Builder stakes(String stakes) { this.stakes = stakes; return this; }
            public Builder keyFactors(List<String> keyFactors) { this.keyFactors = keyFactors; return this; }
            public Builder whatWouldHelp(String whatWouldHelp) { this.whatWouldHelp = whatWouldHelp; return this; }

            public QueryAnalysisDto build() {
                QueryAnalysisDto obj = new QueryAnalysisDto();
                obj.decisionType = this.decisionType;
                obj.decisionSubcategory = this.decisionSubcategory;
                obj.coreTension = this.coreTension;
                obj.emotionalState = this.emotionalState;
                obj.stakes = this.stakes;
                obj.keyFactors = this.keyFactors;
                obj.whatWouldHelp = this.whatWouldHelp;
                return obj;
            }
        }
    }

    public static class StoryDto {
        private String id;
        private String decisionType;
        private String decisionSubcategory;
        private String outcomeSentiment;
        private int timeElapsedMonths;
        private int emotionalRichness;
        private List<String> keyThemes;
        private String hindsightInsight;
        private boolean isCounterNarrative;
        private double compositeScore;

        public StoryDto() {
        }

        public StoryDto(String id, String decisionType, String decisionSubcategory, String outcomeSentiment,
                        int timeElapsedMonths, int emotionalRichness, List<String> keyThemes, String hindsightInsight,
                        boolean isCounterNarrative, double compositeScore) {
            this.id = id;
            this.decisionType = decisionType;
            this.decisionSubcategory = decisionSubcategory;
            this.outcomeSentiment = outcomeSentiment;
            this.timeElapsedMonths = timeElapsedMonths;
            this.emotionalRichness = emotionalRichness;
            this.keyThemes = keyThemes;
            this.hindsightInsight = hindsightInsight;
            this.isCounterNarrative = isCounterNarrative;
            this.compositeScore = compositeScore;
        }

        public String getId() { return id; }
        public void setId(String id) { this.id = id; }

        public String getDecisionType() { return decisionType; }
        public void setDecisionType(String decisionType) { this.decisionType = decisionType; }

        public String getDecisionSubcategory() { return decisionSubcategory; }
        public void setDecisionSubcategory(String decisionSubcategory) { this.decisionSubcategory = decisionSubcategory; }

        public String getOutcomeSentiment() { return outcomeSentiment; }
        public void setOutcomeSentiment(String outcomeSentiment) { this.outcomeSentiment = outcomeSentiment; }

        public int getTimeElapsedMonths() { return timeElapsedMonths; }
        public void setTimeElapsedMonths(int timeElapsedMonths) { this.timeElapsedMonths = timeElapsedMonths; }

        public int getEmotionalRichness() { return emotionalRichness; }
        public void setEmotionalRichness(int emotionalRichness) { this.emotionalRichness = emotionalRichness; }

        public List<String> getKeyThemes() { return keyThemes; }
        public void setKeyThemes(List<String> keyThemes) { this.keyThemes = keyThemes; }

        public String getHindsightInsight() { return hindsightInsight; }
        public void setHindsightInsight(String hindsightInsight) { this.hindsightInsight = hindsightInsight; }

        public boolean isCounterNarrative() { return isCounterNarrative; }
        public void setCounterNarrative(boolean isCounterNarrative) { this.isCounterNarrative = isCounterNarrative; }

        public double getCompositeScore() { return compositeScore; }
        public void setCompositeScore(double compositeScore) { this.compositeScore = compositeScore; }

        public static Builder builder() {
            return new Builder();
        }

        public static class Builder {
            private String id;
            private String decisionType;
            private String decisionSubcategory;
            private String outcomeSentiment;
            private int timeElapsedMonths;
            private int emotionalRichness;
            private List<String> keyThemes;
            private String hindsightInsight;
            private boolean isCounterNarrative;
            private double compositeScore;

            public Builder id(String id) { this.id = id; return this; }
            public Builder decisionType(String decisionType) { this.decisionType = decisionType; return this; }
            public Builder decisionSubcategory(String decisionSubcategory) { this.decisionSubcategory = decisionSubcategory; return this; }
            public Builder outcomeSentiment(String outcomeSentiment) { this.outcomeSentiment = outcomeSentiment; return this; }
            public Builder timeElapsedMonths(int timeElapsedMonths) { this.timeElapsedMonths = timeElapsedMonths; return this; }
            public Builder emotionalRichness(int emotionalRichness) { this.emotionalRichness = emotionalRichness; return this; }
            public Builder keyThemes(List<String> keyThemes) { this.keyThemes = keyThemes; return this; }
            public Builder hindsightInsight(String hindsightInsight) { this.hindsightInsight = hindsightInsight; return this; }
            public Builder isCounterNarrative(boolean isCounterNarrative) { this.isCounterNarrative = isCounterNarrative; return this; }
            public Builder compositeScore(double compositeScore) { this.compositeScore = compositeScore; return this; }

            public StoryDto build() {
                StoryDto obj = new StoryDto();
                obj.id = this.id;
                obj.decisionType = this.decisionType;
                obj.decisionSubcategory = this.decisionSubcategory;
                obj.outcomeSentiment = this.outcomeSentiment;
                obj.timeElapsedMonths = this.timeElapsedMonths;
                obj.emotionalRichness = this.emotionalRichness;
                obj.keyThemes = this.keyThemes;
                obj.hindsightInsight = this.hindsightInsight;
                obj.isCounterNarrative = this.isCounterNarrative;
                obj.compositeScore = this.compositeScore;
                return obj;
            }
        }
    }

    public static class MetadataDto {
        private int totalLatencyMs;
        private boolean liveSearchUsed;
        private boolean agentSearching;
        private int candidatesFound;
        private int storiesPresented;
        private double counterNarrativeRatio;

        public MetadataDto() {
        }

        public MetadataDto(int totalLatencyMs, boolean liveSearchUsed, boolean agentSearching,
                           int candidatesFound, int storiesPresented, double counterNarrativeRatio) {
            this.totalLatencyMs = totalLatencyMs;
            this.liveSearchUsed = liveSearchUsed;
            this.agentSearching = agentSearching;
            this.candidatesFound = candidatesFound;
            this.storiesPresented = storiesPresented;
            this.counterNarrativeRatio = counterNarrativeRatio;
        }

        public int getTotalLatencyMs() { return totalLatencyMs; }
        public void setTotalLatencyMs(int totalLatencyMs) { this.totalLatencyMs = totalLatencyMs; }

        public boolean isLiveSearchUsed() { return liveSearchUsed; }
        public void setLiveSearchUsed(boolean liveSearchUsed) { this.liveSearchUsed = liveSearchUsed; }

        public boolean isAgentSearching() { return agentSearching; }
        public void setAgentSearching(boolean agentSearching) { this.agentSearching = agentSearching; }

        public int getCandidatesFound() { return candidatesFound; }
        public void setCandidatesFound(int candidatesFound) { this.candidatesFound = candidatesFound; }

        public int getStoriesPresented() { return storiesPresented; }
        public void setStoriesPresented(int storiesPresented) { this.storiesPresented = storiesPresented; }

        public double getCounterNarrativeRatio() { return counterNarrativeRatio; }
        public void setCounterNarrativeRatio(double counterNarrativeRatio) { this.counterNarrativeRatio = counterNarrativeRatio; }

        public static Builder builder() {
            return new Builder();
        }

        public static class Builder {
            private int totalLatencyMs;
            private boolean liveSearchUsed;
            private boolean agentSearching;
            private int candidatesFound;
            private int storiesPresented;
            private double counterNarrativeRatio;

            public Builder totalLatencyMs(int totalLatencyMs) { this.totalLatencyMs = totalLatencyMs; return this; }
            public Builder liveSearchUsed(boolean liveSearchUsed) { this.liveSearchUsed = liveSearchUsed; return this; }
            public Builder agentSearching(boolean agentSearching) { this.agentSearching = agentSearching; return this; }
            public Builder candidatesFound(int candidatesFound) { this.candidatesFound = candidatesFound; return this; }
            public Builder storiesPresented(int storiesPresented) { this.storiesPresented = storiesPresented; return this; }
            public Builder counterNarrativeRatio(double counterNarrativeRatio) { this.counterNarrativeRatio = counterNarrativeRatio; return this; }

            public MetadataDto build() {
                MetadataDto obj = new MetadataDto();
                obj.totalLatencyMs = this.totalLatencyMs;
                obj.liveSearchUsed = this.liveSearchUsed;
                obj.agentSearching = this.agentSearching;
                obj.candidatesFound = this.candidatesFound;
                obj.storiesPresented = this.storiesPresented;
                obj.counterNarrativeRatio = this.counterNarrativeRatio;
                return obj;
            }
        }
    }
}
