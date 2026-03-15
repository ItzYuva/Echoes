package com.echoes.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.util.TimeZone;

@SpringBootApplication
public class EchoesApplication {

    static {
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Kolkata"));
        System.setProperty("user.timezone", "Asia/Kolkata");
    }

    public static void main(String[] args) {
        SpringApplication.run(EchoesApplication.class, args);
    }
}
