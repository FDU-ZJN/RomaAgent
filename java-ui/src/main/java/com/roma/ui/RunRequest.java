package com.roma.ui;

public class RunRequest {
    private String title;
    private String idea;
    private String viewpoint;

    private String provider = "agent_framework";
    private String runtime = "openai";
    private String model = "glm-4-flash";
    private String openAiBaseUrl = "https://open.bigmodel.cn/api/paas/v4";
    private String openAiApiKey = "";

    private String searchProvider = "tavily";
    private String tavilyApiKey = "";
    private String maxSources = "3";

    private String senateRejectScoreThreshold = "80";
    private String senateMaxReworkRounds = "2";
    private String articleMinWords = "1200";
    private String articleMaxWords = "1800";

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

