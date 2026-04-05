package com.roma.ui;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class RunRequest {
    private static final int ENV_SEARCH_DEPTH = 8;
    private static final Map<String, String> DOTENV = loadDotEnv();

    private String title;
    private String idea;
    private String viewpoint;

    private String provider = envOrDefault("ROMA_PROVIDER", "mock");
    private String runtime = envOrDefault("ROMA_AGENT_RUNTIME", "auto");
    private String model = envOrDefault("ROMA_MODEL", "gpt-4o-mini");
    private String openAiBaseUrl = envOrDefault("OPENAI_BASE_URL", "");
    private String openAiApiKey = envOrDefault("OPENAI_API_KEY", "");
    private String openAiTimeoutSeconds = envOrDefault("OPENAI_TIMEOUT_SECONDS", "90");
    private String openAiMaxRetries = envOrDefault("OPENAI_MAX_RETRIES", "2");
    private String openAiRetryBackoffSeconds = envOrDefault("OPENAI_RETRY_BACKOFF_SECONDS", "1.5");
    private String openAiMaxTokens = envOrDefault("OPENAI_MAX_TOKENS", "4096");
    private String openAiThinkingType = envOrDefault("OPENAI_THINKING_TYPE", "disabled");

    private String searchProvider = envOrDefault("ROMA_SEARCH_PROVIDER", "tavily");
    private String tavilyApiKey = envOrDefault("TAVILY_API_KEY", "");
    private String maxSources = envOrDefault("ROMA_MAX_SOURCES", "8");

    private String outputDir = envOrDefault("ROMA_OUTPUT_DIR", "output");
    private String enableImageConsul = envOrDefault("ROMA_ENABLE_IMAGE_CONSUL", "false");
    private String imageModel = envOrDefault("ROMA_IMAGE_MODEL", "gpt-image-1");
    private String imageCount = envOrDefault("ROMA_IMAGE_COUNT", "2");
    private String imageSize = envOrDefault("ROMA_IMAGE_SIZE", "512x512");
    private String imagePollIntervalSeconds = envOrDefault("ROMA_IMAGE_POLL_INTERVAL_SECONDS", "3");
    private String imagePollTimeoutSeconds = envOrDefault("ROMA_IMAGE_POLL_TIMEOUT_SECONDS", "180");

    private String senateRejectScoreThreshold = envOrDefault("ROMA_SENATE_REJECT_SCORE_THRESHOLD", "80");
    private String senateMaxReworkRounds = envOrDefault("ROMA_SENATE_MAX_REWORK_ROUNDS", "2");
    private String articleMinWords = envOrDefault("ROMA_ARTICLE_MIN_WORDS", "1200");
    private String articleMaxWords = envOrDefault("ROMA_ARTICLE_MAX_WORDS", "1800");

    private static String envOrDefault(String key, String fallback) {
        String fileValue = DOTENV.get(key);
        if (fileValue != null && !fileValue.isBlank()) {
            return fileValue.trim();
        }
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return value.trim();
    }

    private static Map<String, String> loadDotEnv() {
        Map<String, String> env = new HashMap<>();
        Path envPath = locateEnvFile();
        if (envPath == null) {
            return env;
        }
        try {
            List<String> lines = Files.readAllLines(envPath, StandardCharsets.UTF_8);
            for (String line : lines) {
                String text = line.trim();
                if (text.isEmpty() || text.startsWith("#") || !text.contains("=")) {
                    continue;
                }
                int idx = text.indexOf('=');
                if (idx <= 0) {
                    continue;
                }
                String key = text.substring(0, idx).trim();
                String value = text.substring(idx + 1).trim();
                if ((value.startsWith("\"") && value.endsWith("\"")) || (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.substring(1, value.length() - 1);
                }
                env.put(key, value);
            }
        } catch (IOException ignored) {
            // Keep empty map and fall back to process env + hardcoded defaults.
        }
        return env;
    }

    private static Path locateEnvFile() {
        Path current = Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
        for (int i = 0; i <= ENV_SEARCH_DEPTH && current != null; i++) {
            Path env = current.resolve(".env");
            if (Files.exists(env)) {
                return env;
            }
            current = current.getParent();
        }
        return null;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getIdea() {
        return idea;
    }

    public void setIdea(String idea) {
        this.idea = idea;
    }

    public String getViewpoint() {
        return viewpoint;
    }

    public void setViewpoint(String viewpoint) {
        this.viewpoint = viewpoint;
    }

    public String getProvider() {
        return provider;
    }

    public void setProvider(String provider) {
        this.provider = provider;
    }

    public String getRuntime() {
        return runtime;
    }

    public void setRuntime(String runtime) {
        this.runtime = runtime;
    }

    public String getModel() {
        return model;
    }

    public void setModel(String model) {
        this.model = model;
    }

    public String getOpenAiBaseUrl() {
        return openAiBaseUrl;
    }

    public void setOpenAiBaseUrl(String openAiBaseUrl) {
        this.openAiBaseUrl = openAiBaseUrl;
    }

    public String getOpenAiApiKey() {
        return openAiApiKey;
    }

    public void setOpenAiApiKey(String openAiApiKey) {
        this.openAiApiKey = openAiApiKey;
    }

    public String getOpenAiTimeoutSeconds() {
        return openAiTimeoutSeconds;
    }

    public void setOpenAiTimeoutSeconds(String openAiTimeoutSeconds) {
        this.openAiTimeoutSeconds = openAiTimeoutSeconds;
    }

    public String getOpenAiMaxRetries() {
        return openAiMaxRetries;
    }

    public void setOpenAiMaxRetries(String openAiMaxRetries) {
        this.openAiMaxRetries = openAiMaxRetries;
    }

    public String getOpenAiRetryBackoffSeconds() {
        return openAiRetryBackoffSeconds;
    }

    public void setOpenAiRetryBackoffSeconds(String openAiRetryBackoffSeconds) {
        this.openAiRetryBackoffSeconds = openAiRetryBackoffSeconds;
    }

    public String getOpenAiMaxTokens() {
        return openAiMaxTokens;
    }

    public void setOpenAiMaxTokens(String openAiMaxTokens) {
        this.openAiMaxTokens = openAiMaxTokens;
    }

    public String getOpenAiThinkingType() {
        return openAiThinkingType;
    }

    public void setOpenAiThinkingType(String openAiThinkingType) {
        this.openAiThinkingType = openAiThinkingType;
    }

    public String getSearchProvider() {
        return searchProvider;
    }

    public void setSearchProvider(String searchProvider) {
        this.searchProvider = searchProvider;
    }

    public String getTavilyApiKey() {
        return tavilyApiKey;
    }

    public void setTavilyApiKey(String tavilyApiKey) {
        this.tavilyApiKey = tavilyApiKey;
    }

    public String getMaxSources() {
        return maxSources;
    }

    public void setMaxSources(String maxSources) {
        this.maxSources = maxSources;
    }

    public String getOutputDir() {
        return outputDir;
    }

    public void setOutputDir(String outputDir) {
        this.outputDir = outputDir;
    }

    public String getEnableImageConsul() {
        return enableImageConsul;
    }

    public void setEnableImageConsul(String enableImageConsul) {
        this.enableImageConsul = enableImageConsul;
    }

    public String getImageModel() {
        return imageModel;
    }

    public void setImageModel(String imageModel) {
        this.imageModel = imageModel;
    }

    public String getImageCount() {
        return imageCount;
    }

    public void setImageCount(String imageCount) {
        this.imageCount = imageCount;
    }

    public String getImageSize() {
        return imageSize;
    }

    public void setImageSize(String imageSize) {
        this.imageSize = imageSize;
    }

    public String getImagePollIntervalSeconds() {
        return imagePollIntervalSeconds;
    }

    public void setImagePollIntervalSeconds(String imagePollIntervalSeconds) {
        this.imagePollIntervalSeconds = imagePollIntervalSeconds;
    }

    public String getImagePollTimeoutSeconds() {
        return imagePollTimeoutSeconds;
    }

    public void setImagePollTimeoutSeconds(String imagePollTimeoutSeconds) {
        this.imagePollTimeoutSeconds = imagePollTimeoutSeconds;
    }

    public String getSenateRejectScoreThreshold() {
        return senateRejectScoreThreshold;
    }

    public void setSenateRejectScoreThreshold(String senateRejectScoreThreshold) {
        this.senateRejectScoreThreshold = senateRejectScoreThreshold;
    }

    public String getSenateMaxReworkRounds() {
        return senateMaxReworkRounds;
    }

    public void setSenateMaxReworkRounds(String senateMaxReworkRounds) {
        this.senateMaxReworkRounds = senateMaxReworkRounds;
    }

    public String getArticleMinWords() {
        return articleMinWords;
    }

    public void setArticleMinWords(String articleMinWords) {
        this.articleMinWords = articleMinWords;
    }

    public String getArticleMaxWords() {
        return articleMaxWords;
    }

    public void setArticleMaxWords(String articleMaxWords) {
        this.articleMaxWords = articleMaxWords;
    }
}

