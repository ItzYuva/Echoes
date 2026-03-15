package com.echoes.api.model.enums;

public enum ConfidenceLevel {
    HIGH("high"),
    MEDIUM("medium"),
    LOW("low"),
    INSUFFICIENT("insufficient");

    private final String value;

    ConfidenceLevel(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static ConfidenceLevel fromString(String text) {
        for (ConfidenceLevel level : values()) {
            if (level.value.equalsIgnoreCase(text)) {
                return level;
            }
        }
        return INSUFFICIENT;
    }
}
