from __future__ import annotations

import re
from typing import Callable

from .models import DraftPackage, ResearchPackage
from .providers import LLMProvider


class WriterAgent:
    def __init__(
        self,
        llm: LLMProvider,
        on_log: Callable[[str], None] | None = None,
        on_stream: Callable[[str], None] | None = None,
        min_words: int = 1200,
        max_words: int = 1800,
    ) -> None:
        self.llm = llm
        self.on_log = on_log
        self.on_stream = on_stream
        self.min_words = min_words
        self.max_words = max(max_words, min_words)

    def write(self, research: ResearchPackage, senate_brief: str, rewrite_feedback: str = "") -> DraftPackage:
        title = self._build_title(research.idea)
        outline = ["创意长文"]
        markdown = self._build_markdown(title, research, senate_brief, rewrite_feedback)
        citations = [n.url for n in research.notes]
        return DraftPackage(title=title, outline=outline, markdown=markdown, citations=citations)

    def _build_title(self, idea: str) -> str:
        prompt = "请生成一个有吸引力的中文技术博客标题，长度不超过28字。只输出标题本身。"
        if self.on_log:
            self.on_log("[Stream] 执政官正在生成标题...")
        raw = self.llm.generate(prompt, idea, on_chunk=self.on_stream).strip().splitlines()
        if self.on_stream:
            self.on_stream("\n")
        for line in raw:
            cleaned = line.strip("#- ").strip()
            lowered = cleaned.lower()
            if not cleaned:
                continue
            if lowered.startswith("[mock") or lowered.startswith("model:"):
                continue
            if "system prompt intent" in lowered or lowered.startswith("user request"):
                continue
            if "deterministic placeholder content" in lowered:
                continue
            return cleaned[:120]
        return f"从想法到发布：{idea}"

    def _build_markdown(self, title: str, research: ResearchPackage, senate_brief: str, rewrite_feedback: str) -> str:
        source_notes = "\n".join(f"- {n.title}: {n.summary}" for n in research.notes[:6])
        key_points = "\n".join(f"- {p}" for p in research.key_points)

        system_prompt = (
            "你是一位资深中文作者，擅长写有观点、有画面感、有节奏的长文。"
            "请产出可直接发布的中文 Markdown 正文。"
        )
        user_prompt = (
            f"题目：{title}\n"
            f"选题：{research.idea}\n\n"
            "写作要求：\n"
            "1) 正文必须拆分为 6-8 个 `##` 二级章节，章节之间逻辑递进。\n"
            "2) 避免出现“Hexo 与知乎的平台适配要点”“落地建议与下一步”“调研关键要点”这类机械标题。\n"
            "3) 保持观点鲜明，包含行业判断、案例感、方法论和可执行建议。\n"
            f"4) 长度约 {self.min_words}-{self.max_words} 字。\n"
            "5) 输出格式：仅 Markdown 正文；最后单独保留“## 参考资料”章节。\n\n"
            f"元老院资料包与大纲：\n{senate_brief}\n\n"
            f"元老院2号打回修改意见（如有）：\n{rewrite_feedback or '无'}\n\n"
            f"调研来源摘要：\n{source_notes}\n\n"
            f"可用关键点：\n{key_points}"
        )

        if self.on_log:
            self.on_log("[Stream] 执政官正在撰写正文...")
        raw = self.llm.generate(system_prompt, user_prompt, on_chunk=self.on_stream).strip()
        if self.on_stream:
            self.on_stream("\n")
        if self._looks_like_mock(raw):
            return self._fallback_markdown(title, research, senate_brief)

        cleaned = self._sanitize_generated_markdown(raw)
        if not cleaned:
            return self._fallback_markdown(title, research, senate_brief)
        if len(cleaned) < int(self.min_words * 0.55):
            return self._fallback_markdown(title, research, senate_brief)
        return cleaned

    def _looks_like_mock(self, text: str) -> bool:
        lowered = text.lower()
        return "[mock response]" in lowered or "deterministic placeholder content" in lowered

    def _sanitize_generated_markdown(self, text: str) -> str:
        lines = [line for line in text.splitlines() if not line.strip().lower().startswith(("model:", "system prompt intent:", "user request:"))]
        cleaned = "\n".join(lines).strip()
        if not cleaned:
            return ""
        return cleaned + "\n"

    def _fallback_markdown(self, title: str, research: ResearchPackage, senate_brief: str) -> str:
        core_points = [p for p in research.key_points[:3] if p]
        joined_points = "；".join(core_points) if core_points else "当前公开资料显示产业仍在结构性重塑阶段"
        first_ref = research.notes[0].title if research.notes else "公开行业资料"
        first_summary = research.notes[0].summary[:140] if research.notes else ""
        outline_lines = []
        for line in senate_brief.splitlines():
            text = line.strip()
            if re.match(r"^\d+\.\s", text):
                outline_lines.append(text)
            if len(outline_lines) >= 3:
                break
        outline_hint = "；".join(outline_lines) if outline_lines else "先讲趋势，再讲竞争，再讲行动"

        body = (
            f"# {title}\n\n"
            f"围绕“{research.idea}”这个命题，真正有价值的写法不是罗列概念，而是把证据、趋势和判断拼成一条完整的论证链。"
            f"从目前可得资料看，{joined_points}。这意味着行业讨论不能停留在口号层面，而要回答三个现实问题："
            "增长来自哪里、风险卡在哪些环节、企业该如何分配下一阶段的资源。\n\n"
            f"以 {first_ref} 为代表的资料提示了一个重要信号：{first_summary}。"
            "当这些信息与产业周期、政策节奏、资本偏好叠加后，企业决策的关键不再是“要不要做”，"
            "而是“先做哪一段、用什么节奏做、如何建立可持续护城河”。\n\n"
            f"因此本文采用的推进结构是：{outline_hint}。"
            "在这个框架下，建议把战略目标拆成三层：短期做验证，中期做规模，长期做壁垒。"
            "短期重在找到可复制场景，中期重在形成协同效率，长期重在巩固技术与生态位置。"
            "只有这样，内容讨论才会从“趋势判断”升级为“可执行方案”。\n\n"
            "## 参考资料\n\n"
        )
        refs = "\n".join(f"- [{n.title}]({n.url})" for n in research.notes)
        return body + refs + "\n"
