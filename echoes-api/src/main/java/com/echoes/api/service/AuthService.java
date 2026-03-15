package com.echoes.api.service;

import com.echoes.api.config.AuthConfig;
import com.echoes.api.model.entity.User;
import com.echoes.api.repository.UserRepository;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Date;
import java.util.UUID;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final SecretKey signingKey;
    private final int expiryHours;

    public AuthService(UserRepository userRepository, AuthConfig config) {
        this.userRepository = userRepository;
        // Pad to at least 64 bytes for HS512
        String secret = config.getTokenSecret();
        while (secret.length() < 64) {
            secret = secret + secret;
        }
        this.signingKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expiryHours = config.getTokenExpiryHours();
    }

    public record AuthResult(String userId, String token, boolean intakeCompleted) {}

    public AuthResult register() {
        User user = User.builder()
                .authTokenHash("") // will be set after token generation
                .build();
        user = userRepository.save(user);

        String token = generateToken(user.getId().toString());
        user.setAuthTokenHash(Integer.toHexString(token.hashCode()));
        userRepository.save(user);

        return new AuthResult(user.getId().toString(), token, false);
    }

    public AuthResult login(String userId, String token) {
        String validatedUserId = validateToken(token);
        if (validatedUserId == null || !validatedUserId.equals(userId)) {
            return null;
        }

        User user = userRepository.findById(UUID.fromString(userId)).orElse(null);
        if (user == null) {
            return null;
        }

        user.setLastActiveAt(Instant.now());
        userRepository.save(user);

        return new AuthResult(userId, token, user.isIntakeCompleted());
    }

    public String generateToken(String userId) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(userId)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(expiryHours, ChronoUnit.HOURS)))
                .signWith(signingKey)
                .compact();
    }

    public String validateToken(String token) {
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();
            return claims.getSubject();
        } catch (Exception e) {
            return null;
        }
    }
}
