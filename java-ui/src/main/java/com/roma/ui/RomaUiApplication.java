package com.roma.ui;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.util.HashMap;
import java.util.Map;

@SpringBootApplication
public class RomaUiApplication {
    public static void main(String[] args) {
        int desiredPort = parsePort(System.getenv("ROMA_UI_PORT"), 8080);
        int resolvedPort = findAvailablePort(desiredPort, 20);

        if (resolvedPort != desiredPort) {
            System.out.printf("[CosmosUI] 端口 %d 已占用，自动切换到 %d%n", desiredPort, resolvedPort);
        }

        // Use system property so it takes precedence over application.yml.
        System.setProperty("server.port", String.valueOf(resolvedPort));

        SpringApplication app = new SpringApplication(RomaUiApplication.class);
        Map<String, Object> defaults = new HashMap<>();
        defaults.put("server.port", resolvedPort);
        app.setDefaultProperties(defaults);
        app.run(args);
    }

    private static int parsePort(String value, int defaultPort) {
        if (value == null || value.isBlank()) {
            return defaultPort;
        }
        try {
            int port = Integer.parseInt(value.trim());
            if (port > 0 && port <= 65535) {
                return port;
            }
        } catch (NumberFormatException ignored) {
        }
        return defaultPort;
    }

    private static int findAvailablePort(int startPort, int attempts) {
        int port = startPort;
        for (int i = 0; i <= attempts; i++) {
            if (isPortAvailable(port)) {
                return port;
            }
            port++;
        }
        return startPort;
    }

    private static boolean isPortAvailable(int port) {
        try (ServerSocket socket = new ServerSocket()) {
            socket.setReuseAddress(true);
            socket.bind(new InetSocketAddress("127.0.0.1", port));
            return true;
        } catch (IOException ex) {
            return false;
        }
    }
}

