from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import Settings
from .models import PipelineResult
from .providers import build_image_provider, build_provider
from .publisher import PublisherAgent
from .research import ResearchAgent
from .roman_roles import (
    ConsulAgent,
    GovernorAgent,
    ImageConsulAgent,
    SenateQualityAgent,
    SenateResearchAgent,
    TribuneAgent,
)
from .search import build_search_client
from .writer import WriterAgent


class RomaPipeline:
    def __init__(self, settings: Settings, on_log: Callable[[str], None] | None = None) -> None:
        self.settings = settings
        self.on_log = on_log or (lambda message: print(message, flush=True))
        self.on_stream = lambda chunk: print(chunk, end="", flush=True)
        self.llm = build_provider(settings.provider, settings.model)
        self.image_provider = build_image_provider(settings.provider, settings.image_model, settings.image_size)
        self.search_client = build_search_client(settings.search_provider)
        research_agent = ResearchAgent(
            self.llm,
            self.search_client,
            max_sources=settings.max_sources,
            on_log=self.on_log,
            on_stream=self.on_stream,
        )
        writer_agent = WriterAgent(
            self.llm,
            on_log=self.on_log,
            on_stream=self.on_stream,
            min_words=settings.article_min_words,
            max_words=settings.article_max_words,
        )
        publisher_agent = PublisherAgent()

        self.senate_research_agent = SenateResearchAgent(
            research_agent,
            self.llm,
            on_log=self.on_log,
            on_stream=self.on_stream,
        )
        self.consul_agent = ConsulAgent(writer_agent)
        self.senate_quality_agent = SenateQualityAgent(
            self.llm,
            reject_score_threshold=settings.senate_reject_score_threshold,
            on_log=self.on_log,
            on_stream=self.on_stream,
        )
        self.tribune_agent = TribuneAgent()
        self.image_consul_agent = ImageConsulAgent(
            image_provider=self.image_provider,
            enabled=settings.enable_image_consul,
            image_count=settings.image_count,
            on_log=self.on_log,
        )
        self.governor_agent = GovernorAgent(publisher_agent)

    def run(self, idea: str) -> PipelineResult:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.on_log(f"[Pipeline] Run started: {run_id}")
        self.on_log("[Pipeline] 元老院1号: 检索与方案设计")
        research, senate_design = self.senate_research_agent.run(idea)
        max_rework_rounds = self.settings.senate_max_rework_rounds
        senate_rework_rounds = 0
        senate_rework_triggered = False

        self.on_log("[Pipeline] 执政官: 生成初稿")
        consul_draft = self.consul_agent.run(research, senate_design)
        self.on_log("[Pipeline] 元老院2号: 质量评审")
        senate_reviewed_draft, senate_quality_score, senate_quality_notes, needs_rework = self.senate_quality_agent.run(consul_draft)

        while needs_rework and senate_rework_rounds < max_rework_rounds:
            senate_rework_triggered = True
            senate_rework_rounds += 1
            self.on_log(f"[Pipeline] 元老院2号触发打回，第 {senate_rework_rounds} 轮重写")
            rewrite_feedback = self.senate_quality_agent.build_rework_instruction(
                senate_quality_score,
                senate_quality_notes,
            )
            consul_draft = self.consul_agent.run(research, senate_design, rewrite_feedback)
            senate_reviewed_draft, senate_quality_score, senate_quality_notes, needs_rework = self.senate_quality_agent.run(consul_draft)

        self.on_log("[Pipeline] 保民官: 安全审查")
        tribune_reviewed_draft, tribune_issues = self.tribune_agent.run(senate_reviewed_draft)
        run_dir = Path(self.settings.output_dir) / run_id
        self.on_log("[Pipeline] 图片执政官: 生成配图")
        illustrated_draft = self.image_consul_agent.run(tribune_reviewed_draft, run_dir, senate_design)
        self.on_log("[Pipeline] 行省总督: 多平台部署")
        platform_articles, deployment_records = self.governor_agent.deploy(
            illustrated_draft,
            self.settings.output_dir,
            run_id,
        )

        result = PipelineResult(
            run_id=run_id,
            research=research,
            senate_design=senate_design,
            consul_draft=consul_draft,
            senate_quality_score=senate_quality_score,
            senate_quality_notes=senate_quality_notes,
            senate_rework_rounds=senate_rework_rounds,
            senate_rework_triggered=senate_rework_triggered,
            tribune_issues=tribune_issues,
            draft=illustrated_draft,
            platform_articles=platform_articles,
            deployment_records=deployment_records,
        )
        self._save_result(result)
        self.on_log("[Pipeline] Run finished")
        return result

    def _save_result(self, result: PipelineResult) -> None:
        run_dir = Path(self.settings.output_dir) / result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save full trace payload for auditability and later fine-tuning.
        payload_path = run_dir / "pipeline_result.json"
        payload_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        draft_path = run_dir / "draft.md"
        draft_path.write_text(result.draft.markdown, encoding="utf-8")

        consul_draft_path = run_dir / "consul_draft.md"
        consul_draft_path.write_text(result.consul_draft.markdown, encoding="utf-8")

        senate_brief_path = run_dir / "senate_brief.md"
        senate_brief_path.write_text(result.senate_design, encoding="utf-8")

        tribune_report_path = run_dir / "tribune_report.md"
        tribune_report = "## 保民官审查结果\n\n" + "\n".join(f"- {item}" for item in result.tribune_issues) + "\n"
        tribune_report_path.write_text(tribune_report, encoding="utf-8")

        images_payload_path = run_dir / "images.json"
        images_payload_path.write_text(
            json.dumps([img.__dict__ for img in result.draft.images], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

