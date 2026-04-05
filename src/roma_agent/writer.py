from __future__ import annotations

import json
import re
from typing import Callable

from .models import DraftPackage, ImagePromptSpec, ResearchPackage
from .providers import LLMProvider


IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\{\{IMAGE:([A-Za-z0-9_-]+)\}\}")
IMAGE_PROMPT_COMMENT_PATTERN = re.compile(r"<!--\s*IMAGE_PROMPT\s*(\{[\s\S]*?\})\s*-->")


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
        image_plan = self._extract_image_plan(senate_brief)
        markdown = self._build_markdown(title, research, senate_brief, rewrite_feedback)
        image_prompt_specs = self._extract_image_prompt_specs_from_markdown(markdown)
        if not image_prompt_specs:
            image_prompt_specs = self._build_image_prompt_specs(
                title=title,
                idea=research.idea,
                senate_brief=senate_brief,
                image_plan=image_plan,
                markdown=markdown,
            )
        image_prompt_specs = self._assign_image_ids(image_prompt_specs)
        markdown = self._inject_image_placeholders(markdown, image_prompt_specs)
        markdown = self._inject_prompt_comments_if_missing(markdown, image_prompt_specs)
        citations = [n.url for n in research.notes]
        return DraftPackage(
            title=title,
            outline=outline,
            markdown=markdown,
            citations=citations,
            image_plan=image_plan,
            image_prompt_specs=image_prompt_specs,
        )

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
            "正文禁止插入任何图片 markdown（如 ![](...)）或 <img> 标签，图片由后续流程自动插入。"
            "请在正文里直接给出图片占位符和图片prompt注释。"
            "占位符格式：{{IMAGE:img_x}}。"
            "图片prompt注释格式：<!-- IMAGE_PROMPT {\"image_id\":\"img_x\",\"heading\":\"...\",\"section\":\"...\",\"alt_text\":\"...\",\"prompt\":\"...\",\"rationale\":\"...\"} -->。"
            "IMAGE_PROMPT JSON 各字段值必须是英文。"
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
            "6) 在需要插图的位置插入 {{IMAGE:img_x}}，并紧接着给出对应 IMAGE_PROMPT 注释。\n"
            "7) 不要输出 JSON 包裹正文，直接输出 Markdown。\n\n"
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

    def _extract_image_plan(self, senate_brief: str) -> list[str]:
        if not senate_brief:
            return []
        plans: list[str] = []
        in_section = False
        for line in senate_brief.splitlines():
            text = line.strip()
            if text.startswith("### 图片规划"): 
                in_section = True
                continue
            if in_section and text.startswith("### "):
                break
            if not in_section:
                continue
            cleaned = re.sub(r"^\d+\.\s*", "", text).strip()
            if cleaned:
                plans.append(cleaned)
        return plans

    def _build_image_prompt_specs(
        self,
        title: str,
        idea: str,
        senate_brief: str,
        image_plan: list[str],
        markdown: str,
    ) -> list[ImagePromptSpec]:
        # Fallback only: when embedded IMAGE_PROMPT comments are missing.
        if not image_plan:
            return [
                ImagePromptSpec(
                    heading="Overall Architecture",
                    image_id="img_1",
                    section="Overall Architecture",
                    alt_text=f"Architecture diagram for {title}",
                    prompt=(
                        f"Generate a system architecture diagram for the topic '{title}', highlighting module boundaries, data flows, and component interactions. Style: engineering blueprint, no readable text, no watermark, no brand logo."
                    ),
                    rationale="Fallback when no image plan is available.",
                )
            ]

        fallback_specs: list[ImagePromptSpec] = []
        for idx, item in enumerate(image_plan, start=1):
            heading = self._extract_heading_from_plan(item)
            fallback_specs.append(
                ImagePromptSpec(
                    heading=heading,
                    image_id=f"img_{idx}",
                    section=heading,
                    alt_text=f"Architecture diagram for {heading}",
                    prompt=(
                        f"Generate a technical diagram for the section '{heading}', focusing on module relationships, data flows, and engineering mechanisms. Style: concise, professional, high information density; no readable text, no watermark, no brand logo."
                    ),
                    rationale=item,
                )
            )
        return fallback_specs

    def _extract_image_prompt_specs_from_markdown(self, markdown: str) -> list[ImagePromptSpec]:
        matches = IMAGE_PROMPT_COMMENT_PATTERN.findall(markdown)
        specs: list[ImagePromptSpec] = []
        for raw_json in matches:
            try:
                item = json.loads(raw_json)
            except Exception:
                continue
            if not isinstance(item, dict):
                continue
            image_id = str(item.get("image_id", "")).strip()
            heading = str(item.get("heading", "")).strip() or "Key Section"
            section = str(item.get("section", "")).strip() or heading
            alt_text = str(item.get("alt_text", "")).strip() or f"Architecture diagram for {heading}"
            prompt = str(item.get("prompt", "")).strip()
            rationale = str(item.get("rationale", "")).strip()
            if not prompt:
                continue
            specs.append(
                ImagePromptSpec(
                    heading=heading,
                    image_id=image_id,
                    section=section,
                    alt_text=alt_text,
                    prompt=prompt,
                    rationale=rationale,
                )
            )
        return specs

    def _inject_prompt_comments_if_missing(self, markdown: str, specs: list[ImagePromptSpec]) -> str:
        if not markdown or not specs:
            return markdown

        existing_ids = set()
        for raw_json in IMAGE_PROMPT_COMMENT_PATTERN.findall(markdown):
            try:
                obj = json.loads(raw_json)
                if isinstance(obj, dict) and str(obj.get("image_id", "")).strip():
                    existing_ids.add(str(obj.get("image_id", "")).strip())
            except Exception:
                continue

        additions: list[str] = []
        for spec in specs:
            if not spec.image_id or spec.image_id in existing_ids:
                continue
            payload = {
                "image_id": spec.image_id,
                "heading": spec.heading,
                "section": spec.section,
                "alt_text": spec.alt_text,
                "prompt": spec.prompt,
                "rationale": spec.rationale,
            }
            additions.append(f"{{{{IMAGE:{spec.image_id}}}}}\n<!-- IMAGE_PROMPT {json.dumps(payload, ensure_ascii=False)} -->")

        if not additions:
            return markdown

        block = "\n\n".join(additions)
        ref_match = re.search(r"\n##\s+参考资料\s*\n", markdown)
        if ref_match:
            insert_at = ref_match.start()
            return markdown[:insert_at].rstrip() + "\n\n" + block + "\n\n" + markdown[insert_at:].lstrip("\n")
        return markdown.rstrip() + "\n\n" + block + "\n"

    def _assign_image_ids(self, specs: list[ImagePromptSpec]) -> list[ImagePromptSpec]:
        assigned: list[ImagePromptSpec] = []
        for idx, spec in enumerate(specs, start=1):
            image_id = spec.image_id.strip() if spec.image_id else ""
            if not image_id:
                image_id = f"img_{idx}"
            assigned.append(
                ImagePromptSpec(
                    heading=spec.heading,
                    image_id=image_id,
                    section=spec.section,
                    alt_text=spec.alt_text,
                    prompt=spec.prompt,
                    rationale=spec.rationale,
                )
            )
        return assigned

    def _inject_image_placeholders(self, markdown: str, specs: list[ImagePromptSpec]) -> str:
        if not markdown or not specs:
            return markdown

        text = markdown
        existing_ids = set(IMAGE_PLACEHOLDER_PATTERN.findall(text))
        missing_specs = [spec for spec in specs if spec.image_id and spec.image_id not in existing_ids]
        if not missing_specs:
            return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

        lines = text.splitlines()
        section_indexes: list[int] = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## ") and stripped != "## 参考资料":
                section_indexes.append(idx)

        if not section_indexes:
            placeholders = "\n\n".join(f"{{{{IMAGE:{spec.image_id}}}}}" for spec in missing_specs if spec.image_id)
            if not placeholders:
                return text
            ref_match = re.search(r"\n##\s+参考资料\s*\n", text)
            if ref_match:
                insert_at = ref_match.start()
                return text[:insert_at].rstrip() + "\n\n" + placeholders + "\n\n" + text[insert_at:].lstrip("\n")
            return text.rstrip() + "\n\n" + placeholders + "\n"

        inserts_by_line: dict[int, list[str]] = {}
        for idx, spec in enumerate(missing_specs):
            if not spec.image_id:
                continue
            target_line = section_indexes[min(idx, len(section_indexes) - 1)]
            inserts_by_line.setdefault(target_line, []).append(f"{{{{IMAGE:{spec.image_id}}}}}")

        output: list[str] = []
        for idx, line in enumerate(lines):
            output.append(line)
            inserts = inserts_by_line.get(idx, [])
            if inserts:
                output.append("")
                output.extend(inserts)
                output.append("")

        merged = "\n".join(output)
        merged = re.sub(r"\n{3,}", "\n\n", merged).strip() + "\n"
        return merged

    def _extract_heading_from_plan(self, plan_item: str) -> str:
        match = re.search(r"“(.+?)”", plan_item)
        if match:
            return match.group(1).strip()
        text = plan_item
        text = re.sub(r"建议在", "", text)
        text = re.sub(r"对应段落后插入.*$", "", text)
        text = text.strip(" ：:。")
        return text or "关键章节"
