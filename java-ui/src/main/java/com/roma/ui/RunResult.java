package com.roma.ui;

public class RunResult {
    private boolean success;
    private String runId;
    private String output;
    private String error;
    private String hexoMarkdown;
    private String zhihuMarkdown;
    private String senateBrief;
    private String tribuneReport;

    public boolean isSuccess() {
        return success;
    }

    public void setSuccess(boolean success) {
        this.success = success;
    }

    public String getRunId() {
        return runId;
    }

    public void setRunId(String runId) {
        this.runId = runId;
    }

    public String getOutput() {
        return output;
    }

    public void setOutput(String output) {
        this.output = output;
    }

    public String getError() {
        return error;
    }

    public void setError(String error) {
        this.error = error;
    }

    public String getHexoMarkdown() {
        return hexoMarkdown;
    }

    public void setHexoMarkdown(String hexoMarkdown) {
        this.hexoMarkdown = hexoMarkdown;
    }

    public String getZhihuMarkdown() {
        return zhihuMarkdown;
    }

    public void setZhihuMarkdown(String zhihuMarkdown) {
        this.zhihuMarkdown = zhihuMarkdown;
    }

    public String getSenateBrief() {
        return senateBrief;
    }

    public void setSenateBrief(String senateBrief) {
        this.senateBrief = senateBrief;
    }

    public String getTribuneReport() {
        return tribuneReport;
    }

    public void setTribuneReport(String tribuneReport) {
        this.tribuneReport = tribuneReport;
    }
}

