from __future__ import annotations

from typing import Callable

from .models import ResearchPackage, SourceNote
from .providers import LLMProvider
from .search import SearchClient


class ResearchAgent:
    def __init__(
        self,
        llm: LLMProvider,
        search_client: SearchClient,
        max_sources: int = 8,
        on_log: Callable[[str], None] | None = None,
        on_stream: Callable[[str], None] | None = None,
    ) -> None:
        self.llm = llm
        self.search_client = search_client
        self.max_sources = max_sources
        self.on_log = on_log
        self.on_stream = on_stream

    def run(self, idea: str) -> ResearchPackage:
        search_queries = self._build_queries(idea)
        notes = self._collect_web_notes(search_queries)
        if not notes:
            notes = self._collect_seed_notes(idea)

        key_points_prompt = (
            "请从资料中提取 5 条不重复的中文关键观点，每条单独一行，不要编号。"
        )
        notes_text = "\n".join(f"- {n.title}: {n.summary}" for n in notes)
        if self.on_log:
            self.on_log("[Stream] 元老院1号正在提取关键观点...")
        model_response = self.llm.generate(key_points_prompt, notes_text, on_chunk=self.on_stream)
        if self.on_stream:
            self.on_stream("\n")
        key_points = []
        for line in model_response.splitlines():
            cleaned = line.strip("- ").strip()
            lowered = cleaned.lower()
            if not cleaned:
                continue
            if lowered.startswith("[mock") or lowered.startswith("model:"):
                continue
            if lowered.startswith("system prompt intent") or lowered.startswith("user request"):
                continue
            if "deterministic placeholder content" in lowered:
                continue
            key_points.append(cleaned)
        if not key_points:
            key_points = [
                "先界定真实读者痛点，再展开论证。",
                "关键事实必须附带可信来源链接。",
                "将方法论与可执行步骤结合，避免空泛口号。",
                "根据发布平台调整叙事节奏与表达风格。",
                "建立可复用的评估指标，持续优化内容质量。",
            ]

        return ResearchPackage(
            idea=idea,
            search_queries=search_queries,
            notes=notes,
            key_points=key_points[:5],
        )

    def _collect_web_notes(self, queries: list[str]) -> list[SourceNote]:
        gathered: list[SourceNote] = []
        seen_urls: set[str] = set()
        query_limit = max(1, min(3, len(queries)))
        per_query = max(2, self.max_sources // query_limit)

        for query in queries[:query_limit]:
            try:
                results = self.search_client.search(query, max_results=per_query)
            except Exception:
                continue
            for item in results:
                if item.url in seen_urls:
                    continue
                gathered.append(item)
                seen_urls.add(item.url)
                if len(gathered) >= self.max_sources:
                    return gathered
        return gathered

    def _build_queries(self, idea: str) -> list[str]:
        return [
            f"{idea} best practices",
            f"{idea} case study",
            f"{idea} common mistakes",
            f"{idea} implementation guide",
            f"{idea} metrics and evaluation",
        ]

    def _collect_seed_notes(self, idea: str) -> list[SourceNote]:
        seed = [
            SourceNote(
                title="Microsoft Agent Framework Overview",
                url="https://learn.microsoft.com/en-us/agent-framework/overview/",
                summary="Agent Framework provides multi-agent orchestration, tools, and workflow execution patterns.",
                confidence=0.9,
            ),
            SourceNote(
                title="Agent Framework Python Samples",
                url="https://github.com/microsoft/agent-framework/tree/main/python/samples",
                summary="Python samples show progressive patterns from basic agents to workflows and hosting.",
                confidence=0.88,
            ),
            SourceNote(
                title="Content Workflow Design",
                url="https://example.com/content-workflow-design",
                summary=(
                    "A robust content pipeline includes research, outlining, drafting, quality review, "
                    "and platform-specific transformation."
                ),
                confidence=0.55,
            ),
        ]
        custom = SourceNote(
            title=f"Problem framing for: {idea}",
            url="https://example.com/idea-specific-notes",
            summary="Translate the idea into audience pain points, actionable steps, and measurable outcomes.",
            confidence=0.5,
        )
        items = seed + [custom]
        return items[: self.max_sources]
