package com.roma.ui;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Controller
public class UiController {
    private final PipelineRunnerService pipelineRunnerService;
    private final ObjectMapper objectMapper;
    private final Map<String, RunRequest> pendingRequests = new ConcurrentHashMap<>();

    public UiController(PipelineRunnerService pipelineRunnerService, ObjectMapper objectMapper) {
        this.pipelineRunnerService = pipelineRunnerService;
        this.objectMapper = objectMapper;
    }

    @GetMapping("/")
    public String index(Model model) {
        model.addAttribute("request", new RunRequest());
        model.addAttribute("result", null);
        return "index";
    }

    @PostMapping("/run")
    public String run(@ModelAttribute("request") RunRequest request, Model model) {
        RunResult result = pipelineRunnerService.runPipeline(request);
        model.addAttribute("result", result);
        return "index";
    }

    @PostMapping("/run/prepare")
    @ResponseBody
    public Map<String, String> prepare(@ModelAttribute RunRequest request) {
        String token = UUID.randomUUID().toString();
        pendingRequests.put(token, copyRequest(request));
        return Map.of("token", token);
    }

    @GetMapping(path = "/run/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE + ";charset=UTF-8")
    @ResponseBody
    public SseEmitter stream(@RequestParam("token") String token) {
        SseEmitter emitter = new SseEmitter(0L);
        RunRequest request = pendingRequests.remove(token);

        if (request == null) {
            try {
                emit(emitter, "run_error", "运行令牌无效或已过期，请重新提交。");
            } catch (IOException ignored) {
            }
            emitter.complete();
            return emitter;
        }

        CompletableFuture.runAsync(() -> {
            try {
                emit(emitter, "status", "开始执行写作流水线...");
                RunResult result = pipelineRunnerService.runPipeline(request, chunk -> {
                    try {
                        emit(emitter, "chunk", chunk);
                    } catch (IOException ex) {
                        throw new RuntimeException(ex);
                    }
                });
                emit(emitter, "result", objectMapper.writeValueAsString(result));
                emitter.complete();
            } catch (Exception ex) {
                try {
                    emit(emitter, "run_error", "执行失败: " + ex.getMessage());
                } catch (IOException ignored) {
                }
                emitter.completeWithError(ex);
            }
        });

        return emitter;
    }

    private static void emit(SseEmitter emitter, String event, String data) throws IOException {
        emitter.send(SseEmitter.event().name(event).data(data));
    }

    private static RunRequest copyRequest(RunRequest source) {
        RunRequest target = new RunRequest();
        target.setTitle(source.getTitle());
        target.setIdea(source.getIdea());
        target.setViewpoint(source.getViewpoint());
        target.setProvider(source.getProvider());
        target.setRuntime(source.getRuntime());
        target.setModel(source.getModel());
        target.setOpenAiBaseUrl(source.getOpenAiBaseUrl());
        target.setOpenAiApiKey(source.getOpenAiApiKey());
        target.setSearchProvider(source.getSearchProvider());
        target.setTavilyApiKey(source.getTavilyApiKey());
        target.setMaxSources(source.getMaxSources());
        target.setSenateRejectScoreThreshold(source.getSenateRejectScoreThreshold());
        target.setSenateMaxReworkRounds(source.getSenateMaxReworkRounds());
        target.setArticleMinWords(source.getArticleMinWords());
        target.setArticleMaxWords(source.getArticleMaxWords());
        return target;
    }
}

