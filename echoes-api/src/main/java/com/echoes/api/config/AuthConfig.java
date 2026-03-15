package com.echoes.api.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "echoes.auth")
public class AuthConfig {
    private String tokenSecret = "echoes-dev-secret-change-in-production-please";
    private int tokenExpiryHours = 720;

    public String getTokenSecret() {
        return tokenSecret;
    }

    public void setTokenSecret(String tokenSecret) {
        this.tokenSecret = tokenSecret;
    }

    public int getTokenExpiryHours() {
        return tokenExpiryHours;
    }

    public void setTokenExpiryHours(int tokenExpiryHours) {
        this.tokenExpiryHours = tokenExpiryHours;
    }
}
