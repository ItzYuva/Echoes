package com.echoes.api.controller;

import com.echoes.api.model.dto.ProfileResponseDto;
import com.echoes.api.model.dto.ValuesVectorDto;
import com.echoes.api.service.ProfileService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/profile")
public class ProfileController {

    private final ProfileService profileService;

    public ProfileController(ProfileService profileService) {
        this.profileService = profileService;
    }

    @GetMapping("/{userId}")
    public ResponseEntity<ProfileResponseDto> getProfile(@PathVariable String userId) {
        return ResponseEntity.ok(profileService.getProfile(userId));
    }

    @PutMapping("/{userId}")
    public ResponseEntity<Map<String, String>> updateProfile(@PathVariable String userId,
                                                              @RequestBody ValuesVectorDto valuesVector,
                                                              Authentication auth) {
        profileService.updateProfile(userId, valuesVector);
        return ResponseEntity.ok(Map.of("status", "updated"));
    }
}
