from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from .models import DeploymentRecord, DraftPackage, ImageAsset, PlatformArticle, ResearchPackage, SourceNote
from .providers import ImageProvider, LLMProvider
from .publisher import PublisherAgent
from .research import ResearchAgent
from .writer import WriterAgent


class SenateResearchAgent:
    """元老院 Agent 1: 负责检索与总体方案设计。"""

    def __init__(
        self,
        research_agent: ResearchAgent,
        llm: LLMProvider,
        on_log: Callable[[str], None] | None = None,
        on_stream: Callable[[str], None] | None = None,
    ) -> None:
        self.research_agent = research_agent
        self.llm = llm
        self.on_log = on_log
        self.on_stream = on_stream

    def run(self, idea: str) -> tuple[ResearchPackage, str]:
        research = self.research_agent.run(idea)
        return research, self._build_research_brief(idea, research)

    def _build_research_brief(self, idea: str, research: ResearchPackage) -> str:
        outline_prompt = (
            "请基于给定资料输出中文写作大纲，6-8 个一级要点。"
            "仅输出要点列表，每行一条。"
        )
        notes_text = "\n".join(f"- {item.title}: {item.summary}" for item in research.notes)
        if self.on_log:
            self.on_log("[Stream] 元老院1号正在生成资料大纲...")
        outline_raw = self.llm.generate(
            outline_prompt,
            f"选题：{idea}\n\n资料：\n{notes_text}",
            on_chunk=self.on_stream,
        )
        if self.on_stream:
            self.on_stream("\n")
        outline_lines: list[str] = []
        for line in outline_raw.splitlines():
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
            outline_lines.append(cleaned)

        if not outline_lines:
            outline_lines = [
                "行业演进脉络与关键转折点",
                "市场规模与结构性机会",
                "产业链关键环节与竞争格局",
                "技术路线与政策变量",
                "代表性企业与案例观察",
                "未来三年的机会与风险判断",
                "行动建议与落地路径",
            ]

        core_data = self._extract_core_data(research.notes)
        lines: list[str] = ["## 元老院资料包", "", f"选题：{idea}", "", "### 可参考资料（网址/PDF）", ""]
        for idx, note in enumerate(research.notes, start=1):
            kind = "PDF" if ".pdf" in note.url.lower() or "pdf" in note.title.lower() else "网页"
            lines.append(f"{idx}. [{note.title}]({note.url}) | 类型：{kind} | 可信度：{note.confidence:.2f}")

        lines.extend(["", "### 可引用核心数据", ""])
        if core_data:
            for idx, item in enumerate(core_data, start=1):
                lines.append(f"{idx}. {item}")
        else:
            lines.append("1. 当前资料未提取到明确数字，请补充含市场规模、增速、份额的数据来源。")

        lines.extend(["", "### 建议大纲", ""])
        for idx, item in enumerate(outline_lines[:8], start=1):
            lines.append(f"{idx}. {item}")

        lines.extend(["", "### 图片位置建议（供图片执政官）", ""])
        distributed_items = self._pick_distributed_outline_items(outline_lines, 4)
        for idx, item in enumerate(distributed_items, start=1):
            lines.append(f"{idx}. 建议在“{item}”对应段落后插入架构解释型配图。")

        lines.extend(
            [
                "",
                "### 写作要求",
                "",
                "- 执政官需优先引用上述资料与数据，不得脱离选题泛泛而谈。",
                "- 每个关键判断尽量对应至少一条可追溯来源。",
                "- 正文需拆分为多个章节（建议 6-8 个二级章节），方便分段配图。",
                "- 文章应体现行业洞察、案例分析与可执行建议。",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def _pick_distributed_outline_items(self, items: list[str], count: int) -> list[str]:
        if not items:
            return []
        if len(items) <= count:
            return items

        selected: list[str] = []
        for i in range(count):
            idx = round(i * (len(items) - 1) / (count - 1))
            value = items[idx]
            if value not in selected:
                selected.append(value)
        return selected

    def _extract_core_data(self, notes: list[SourceNote]) -> list[str]:
        items: list[str] = []
        number_pattern = re.compile(r"\d")
        for note in notes:
            summary = getattr(note, "summary", "")
            for seg in re.split(r"[\n。；;]", summary):
                text = seg.strip()
                if len(text) < 12:
                    continue
                if not number_pattern.search(text):
                    continue
                if text not in items:
                    items.append(text)
                if len(items) >= 8:
                    return items
        return items


class ConsulAgent:
    """执政官: 依据元老院调研结果与方案完成完整博客。"""

    def __init__(self, writer_agent: WriterAgent) -> None:
        self.writer_agent = writer_agent

    def run(self, research: ResearchPackage, senate_design: str, rewrite_feedback: str = "") -> DraftPackage:
        return self.writer_agent.write(research, senate_design, rewrite_feedback)


class SenateQualityAgent:
    """元老院 Agent 2: 负责质量评分与简单修订。"""

    def __init__(
        self,
        llm: LLMProvider,
        reject_score_threshold: float = 80.0,
        on_log: Callable[[str], None] | None = None,
        on_stream: Callable[[str], None] | None = None,
    ) -> None:
        self.llm = llm
        self.reject_score_threshold = reject_score_threshold
        self.reject_issue_threshold = 4
        self.on_log = on_log
        self.on_stream = on_stream

    def run(self, draft: DraftPackage) -> tuple[DraftPackage, float, list[str], bool]:
        score, notes = self._llm_rubric_score(draft)
        revised_markdown = self._simple_edit(draft.markdown, score, notes)
        revised_draft = DraftPackage(
            title=draft.title,
            outline=draft.outline,
            markdown=revised_markdown,
            citations=draft.citations,
        )
        rounded = min(100.0, round(score, 2))
        needs_rework = self._should_rework(rounded, notes)
        return revised_draft, rounded, notes, needs_rework

    def build_rework_instruction(self, score: float, notes: list[str]) -> str:
        note_text = "\n".join(f"- {item}" for item in notes[:6])
        return (
            f"元老院2号审查未通过（当前分数 {score:.2f}）。"
            "请根据以下问题进行实质性重写，而不是表层润色：\n"
            f"{note_text}\n"
            "要求：补充证据、增强论证、优化结构，并确保与选题强相关。"
        )

    def _should_rework(self, score: float, notes: list[str]) -> bool:
        actionable = [n for n in notes if "建议" in n or "不足" in n or "缺" in n]
        if score < self.reject_score_threshold:
            return True
        if len(actionable) >= self.reject_issue_threshold:
            return True
        return False

    def _llm_rubric_score(self, draft: DraftPackage) -> tuple[float, list[str]]:
        system_prompt = (
            "你是元老院质控官，请对文章按量表评分："
            "结构(25)、事实依据(25)、表达清晰度(20)、实用价值(20)、风格一致性(10)。"
            "仅返回 JSON，字段固定为 score、notes、minor_revisions。"
            "notes 用中文短句，3 条。minor_revisions 最多 3 条中文短建议。"
        )
        user_prompt = (
            f"Title: {draft.title}\n"
            f"Citations: {len(draft.citations)}\n\n"
            f"Article:\n{draft.markdown}"
        )

        if self.on_log:
            self.on_log("[Stream] 元老院2号正在进行量表审查...")
        raw = self.llm.generate(system_prompt, user_prompt, on_chunk=self.on_stream)
        if self.on_stream:
            self.on_stream("\n")
        parsed = self._parse_llm_json(raw)
        if parsed is not None:
            score = self._normalize_score(parsed.get("score", 0.0))
            notes = [str(item).strip() for item in parsed.get("notes", []) if str(item).strip()]
            edits = [str(item).strip() for item in parsed.get("minor_revisions", []) if str(item).strip()]
            merged = notes + [f"Suggested edit: {item}" for item in edits]
            if not merged:
                merged = ["量表返回为空，保持当前稿件并做最小改动。"]
            return max(0.0, min(100.0, score)), merged[:6]

        return self._fallback_score(draft)

    def _parse_llm_json(self, raw: str) -> dict[str, object] | None:
        try:
            return json.loads(raw)
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _fallback_score(self, draft: DraftPackage) -> tuple[float, list[str]]:
        score = 65.0
        notes: list[str] = ["LLM 量表暂不可用，已启用启发式评分兜底。"]

        heading_count = draft.markdown.count("## ")
        citation_count = len(draft.citations)
        body_length = len(draft.markdown)

        score += min(15.0, heading_count * 2.0)
        score += min(12.0, citation_count * 2.0)
        score += 8.0 if body_length >= 1800 else 4.0

        if heading_count >= 6:
            notes.append("结构清晰，便于快速浏览。")
        else:
            notes.append("建议补充分节标题以提升可读性。")

        if citation_count >= 3:
            notes.append("证据链可追溯性较好。")
        else:
            notes.append("建议增加高可信来源以提升说服力。")

        return score, notes

    def _normalize_score(self, raw_score: object) -> float:
        if isinstance(raw_score, (int, float)):
            return float(raw_score)
        if isinstance(raw_score, str):
            try:
                return float(raw_score.strip())
            except Exception:
                return 0.0
        if isinstance(raw_score, dict):
            values: list[float] = []
            for value in raw_score.values():
                if isinstance(value, (int, float)):
                    values.append(float(value))
                elif isinstance(value, str):
                    try:
                        values.append(float(value.strip()))
                    except Exception:
                        continue
            if values:
                return sum(values)
        return 0.0

    def _simple_edit(self, markdown: str, score: float, notes: list[str]) -> str:
        compacted = re.sub(r"\n{3,}", "\n\n", markdown).strip() + "\n"
        compacted += "\n## 元老院质控意见\n\n"
        for note in notes[:6]:
            compacted += f"- {note}\n"
        compacted += f"\n> Senate quality score: {score:.2f}/100\n"
        return compacted


class TribuneAgent:
    """保民官: 负责安全与隐私审查并简单修改。"""

    def run(self, draft: DraftPackage) -> tuple[DraftPackage, list[str]]:
        issues: list[str] = []
        text = draft.markdown

        patterns = [
            (r"sk-[A-Za-z0-9]{20,}", "sk-***REDACTED***", "发现疑似 API Key，已脱敏处理。"),
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", "发现邮箱信息，已脱敏处理。"),
            (r"(?<!\d)1\d{10}(?!\d)", "[REDACTED_PHONE]", "发现手机号信息，已脱敏处理。"),
        ]

        for pattern, replacement, issue in patterns:
            updated = re.sub(pattern, replacement, text)
            if updated != text:
                issues.append(issue)
                text = updated

        if not issues:
            issues.append("未发现明显密钥或个人敏感信息。")

        text = text.strip() + "\n"
        revised = DraftPackage(
            title=draft.title,
            outline=draft.outline,
            markdown=text,
            citations=draft.citations,
            images=draft.images,
        )
        return revised, issues


class ImageConsulAgent:
    """图片执政官: 根据定稿内容生成配图并附加到草稿元数据。"""

    def __init__(
        self,
        image_provider: ImageProvider,
        enabled: bool,
        image_count: int,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.image_provider = image_provider
        self.enabled = enabled
        self.image_count = max(0, image_count)
        self.on_log = on_log

    def run(self, draft: DraftPackage, run_dir: Path, senate_design: str = "") -> DraftPackage:
        if not self.enabled or self.image_count <= 0:
            return draft

        image_dir = run_dir / "images"
        prompts = self._build_image_prompts(draft, senate_design)
        assets: list[ImageAsset] = []

        for idx, item in enumerate(prompts[: self.image_count], start=1):
            alt_text = item["alt"]
            prompt = item["prompt"]
            if self.on_log:
                self.on_log(f"[Pipeline] 图片执政官: 正在生成第 {idx} 张配图")
            try:
                asset = self.image_provider.generate_image(
                    prompt=prompt,
                    output_dir=image_dir,
                    name_prefix=f"img_{idx}",
                    alt_text=alt_text,
                )
            except Exception as exc:  # noqa: BLE001
                asset = ImageAsset(
                    alt_text=alt_text,
                    prompt=prompt,
                    status=f"failed: {exc}",
                )
            assets.append(asset)

        return DraftPackage(
            title=draft.title,
            outline=draft.outline,
            markdown=draft.markdown,
            citations=draft.citations,
            images=assets,
        )

    def _build_image_prompts(self, draft: DraftPackage, senate_design: str) -> list[dict[str, str]]:
        placement_targets = self._extract_image_targets(senate_design)
        sections = re.split(r"^##\s+", draft.markdown, flags=re.MULTILINE)
        core_items: list[tuple[str, str]] = []
        excluded = {
            "参考资料",
            "结语",
            "元老院质控意见",
            "保民官审查结果",
        }

        for part in sections[1:]:
            lines = part.splitlines()
            if not lines:
                continue
            heading = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if not heading or heading in excluded:
                continue
            if len(body) < 60:
                continue
            core_items.append((heading, body[:260]))

        if not core_items:
            return [
                {
                    "alt": f"架构解释配图：{draft.title}",
                    "prompt": (
                        f"围绕技术主题“{draft.title}”生成系统架构示意图风格插图，"
                        "突出模块边界、调用链路、计算与存储协同关系，"
                        "强调架构解释，不要封面风格。"
                        "不要可读文字、不要水印、不要品牌logo。"
                    ),
                }
            ]

        # Senate targets decide priority order, but should not collapse total image count.
        prioritized: list[tuple[str, str]] = []
        used_headings: set[str] = set()
        if placement_targets:
            for target in placement_targets:
                for heading, snippet in core_items:
                    if target in heading and heading not in used_headings:
                        prioritized.append((heading, snippet))
                        used_headings.add(heading)

        for heading, snippet in core_items:
            if heading not in used_headings:
                prioritized.append((heading, snippet))
                used_headings.add(heading)

        prompts: list[dict[str, str]] = []
        for heading, snippet in prioritized[: self.image_count]:
            prompts.append(
                {
                    "alt": f"架构解释配图：{heading}",
                    "prompt": (
                        f"为技术文章章节“{heading}”生成架构解释型信息图。"
                        "画面应体现系统组件关系、数据流向、模块分层与交互路径，"
                        "强调工程结构与技术机制，不要海报封面风格。"
                        f"章节核心语义：{snippet}。"
                        "风格：简洁专业、工程蓝图感、信息密度高；"
                        "不要可读文字、不要水印、不要品牌logo。"
                    ),
                }
            )

        # If image_count is larger than unique sections, create senate-prioritized variants.
        if placement_targets and len(prompts) < self.image_count:
            base = prompts[:] if prompts else []
            variant_no = 2
            idx = 0
            while base and len(prompts) < self.image_count:
                item = base[idx % len(base)]
                heading = item["alt"].replace("架构解释配图：", "", 1).strip()
                prompts.append(
                    {
                        "alt": f"架构解释配图：{heading}-变体{variant_no}",
                        "prompt": item["prompt"] + f" 同一章节生成第{variant_no}个视觉变体，强调不同视角。",
                    }
                )
                idx += 1
                if idx % len(base) == 0:
                    variant_no += 1

        if not prompts:
            prompts.append(
                {
                    "alt": f"架构解释配图：{draft.title}",
                    "prompt": (
                        f"围绕技术主题“{draft.title}”生成系统架构示意图风格插图，"
                        "突出模块边界、调用链路、计算与存储协同关系，"
                        "强调架构解释，不要封面风格。"
                        "不要可读文字、不要水印、不要品牌logo。"
                    ),
                }
            )
        return prompts

    def _extract_image_targets(self, senate_design: str) -> list[str]:
        if not senate_design:
            return []
        targets: list[str] = []
        in_section = False
        for line in senate_design.splitlines():
            text = line.strip()
            if text.startswith("### 图片位置建议"):
                in_section = True
                continue
            if in_section and text.startswith("### "):
                break
            if not in_section:
                continue
            match = re.search(r"“(.+?)”", text)
            if match:
                targets.append(match.group(1).strip())
        return targets


class GovernorAgent:
    """行省总督: 负责部署保民官审查后的博客。"""

    def __init__(self, publisher: PublisherAgent) -> None:
        self.publisher = publisher

    def deploy(self, draft: DraftPackage, output_root: Path, run_id: str) -> tuple[list[PlatformArticle], list[DeploymentRecord]]:
        articles = self.publisher.publish_variants(draft)
        deployment_dir = output_root / run_id / "deployments"
        deployment_dir.mkdir(parents=True, exist_ok=True)

        records: list[DeploymentRecord] = []
        for article in articles:
            target = deployment_dir / f"{article.platform}.md"
            target.write_text(article.markdown, encoding="utf-8")
            records.append(
                DeploymentRecord(
                    platform=article.platform,
                    output_path=str(target).replace("\\", "/"),
                    status="deployed",
                )
            )
        return articles, records
