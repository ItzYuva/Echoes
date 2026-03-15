package com.echoes.api.model.dto;

import java.util.HashMap;
import java.util.Map;

public class ValuesVectorDto {
    private double riskTolerance;
    private double changeOrientation;
    private double securityVsGrowth;
    private double actionBias;
    private double socialWeight;
    private double timeHorizon;
    private double lossSensitivity;
    private double ambiguityTolerance;

    public ValuesVectorDto() {
    }

    public ValuesVectorDto(double riskTolerance, double changeOrientation, double securityVsGrowth, double actionBias,
                           double socialWeight, double timeHorizon, double lossSensitivity, double ambiguityTolerance) {
        this.riskTolerance = riskTolerance;
        this.changeOrientation = changeOrientation;
        this.securityVsGrowth = securityVsGrowth;
        this.actionBias = actionBias;
        this.socialWeight = socialWeight;
        this.timeHorizon = timeHorizon;
        this.lossSensitivity = lossSensitivity;
        this.ambiguityTolerance = ambiguityTolerance;
    }

    public double getRiskTolerance() { return riskTolerance; }
    public void setRiskTolerance(double riskTolerance) { this.riskTolerance = riskTolerance; }

    public double getChangeOrientation() { return changeOrientation; }
    public void setChangeOrientation(double changeOrientation) { this.changeOrientation = changeOrientation; }

    public double getSecurityVsGrowth() { return securityVsGrowth; }
    public void setSecurityVsGrowth(double securityVsGrowth) { this.securityVsGrowth = securityVsGrowth; }

    public double getActionBias() { return actionBias; }
    public void setActionBias(double actionBias) { this.actionBias = actionBias; }

    public double getSocialWeight() { return socialWeight; }
    public void setSocialWeight(double socialWeight) { this.socialWeight = socialWeight; }

    public double getTimeHorizon() { return timeHorizon; }
    public void setTimeHorizon(double timeHorizon) { this.timeHorizon = timeHorizon; }

    public double getLossSensitivity() { return lossSensitivity; }
    public void setLossSensitivity(double lossSensitivity) { this.lossSensitivity = lossSensitivity; }

    public double getAmbiguityTolerance() { return ambiguityTolerance; }
    public void setAmbiguityTolerance(double ambiguityTolerance) { this.ambiguityTolerance = ambiguityTolerance; }

    public Map<String, Double> toSnakeCaseMap() {
        Map<String, Double> map = new HashMap<>();
        map.put("risk_tolerance", riskTolerance);
        map.put("change_orientation", changeOrientation);
        map.put("security_vs_growth", securityVsGrowth);
        map.put("action_bias", actionBias);
        map.put("social_weight", socialWeight);
        map.put("time_horizon", timeHorizon);
        map.put("loss_sensitivity", lossSensitivity);
        map.put("ambiguity_tolerance", ambiguityTolerance);
        return map;
    }

    public static ValuesVectorDto fromSnakeCaseMap(Map<String, Object> map) {
        return ValuesVectorDto.builder()
                .riskTolerance(toDouble(map.get("risk_tolerance")))
                .changeOrientation(toDouble(map.get("change_orientation")))
                .securityVsGrowth(toDouble(map.get("security_vs_growth")))
                .actionBias(toDouble(map.get("action_bias")))
                .socialWeight(toDouble(map.get("social_weight")))
                .timeHorizon(toDouble(map.get("time_horizon")))
                .lossSensitivity(toDouble(map.get("loss_sensitivity")))
                .ambiguityTolerance(toDouble(map.get("ambiguity_tolerance")))
                .build();
    }

    private static double toDouble(Object val) {
        if (val instanceof Number n) return n.doubleValue();
        if (val instanceof String s) return Double.parseDouble(s);
        return 0.5;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private double riskTolerance;
        private double changeOrientation;
        private double securityVsGrowth;
        private double actionBias;
        private double socialWeight;
        private double timeHorizon;
        private double lossSensitivity;
        private double ambiguityTolerance;

        public Builder riskTolerance(double riskTolerance) { this.riskTolerance = riskTolerance; return this; }
        public Builder changeOrientation(double changeOrientation) { this.changeOrientation = changeOrientation; return this; }
        public Builder securityVsGrowth(double securityVsGrowth) { this.securityVsGrowth = securityVsGrowth; return this; }
        public Builder actionBias(double actionBias) { this.actionBias = actionBias; return this; }
        public Builder socialWeight(double socialWeight) { this.socialWeight = socialWeight; return this; }
        public Builder timeHorizon(double timeHorizon) { this.timeHorizon = timeHorizon; return this; }
        public Builder lossSensitivity(double lossSensitivity) { this.lossSensitivity = lossSensitivity; return this; }
        public Builder ambiguityTolerance(double ambiguityTolerance) { this.ambiguityTolerance = ambiguityTolerance; return this; }

        public ValuesVectorDto build() {
            ValuesVectorDto obj = new ValuesVectorDto();
            obj.riskTolerance = this.riskTolerance;
            obj.changeOrientation = this.changeOrientation;
            obj.securityVsGrowth = this.securityVsGrowth;
            obj.actionBias = this.actionBias;
            obj.socialWeight = this.socialWeight;
            obj.timeHorizon = this.timeHorizon;
            obj.lossSensitivity = this.lossSensitivity;
            obj.ambiguityTolerance = this.ambiguityTolerance;
            return obj;
        }
    }
}
