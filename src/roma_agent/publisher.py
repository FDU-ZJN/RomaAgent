from __future__ import annotations

import re
from datetime import datetime

from .models import DraftPackage, PlatformArticle


class PublisherAgent:
    IMAGE_PLACEHOLDER_PATTERN = re.compile(r"\{\{IMAGE:([A-Za-z0-9_-]+)\}\}")
    IMAGE_PLACEHOLDER_IN_MARKDOWN_IMAGE_PATTERN = re.compile(
        r"!\[\s*\{\{IMAGE:([A-Za-z0-9_-]+)\}\}\s*\]\([^\)]*\)",
        re.IGNORECASE,
    )

    def _strip_outer_code_fence(self, markdown: str) -> str:
        text = markdown.strip()
        # Remove whole-document fenced wrapper like ```markdown ... ```
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip() + "\n"
        return markdown

    def _image_markdown(self, draft: DraftPackage, platform: str) -> tuple[dict[str, str], list[str]]:
        by_id: dict[str, str] = {}
        unassigned: list[str] = []
        for item in draft.images:
            if item.status != "generated":
                continue
            if item.source_url:
                src = item.source_url
            elif item.relative_path:
                src = f"../{item.relative_path}" if platform == "hexo" else item.relative_path
            else:
                continue
            md = f"![{item.alt_text}]({src})"
            image_id = getattr(item, "image_id", "").strip()
            if image_id:
                by_id[image_id] = md
            else:
                unassigned.append(md)
        return by_id, unassigned

    def _inject_images_into_markdown(self, markdown: str, draft: DraftPackage, platform: str) -> str:
        if not draft.images:
            return markdown

        # Normalize model outputs like ![{{IMAGE:img_1}}](#) to raw placeholders
        # so placeholders are not removed by generic image markdown cleanup.
        markdown = self.IMAGE_PLACEHOLDER_IN_MARKDOWN_IMAGE_PATTERN.sub(
            lambda m: "{{IMAGE:" + m.group(1) + "}}",
            markdown,
        )
        markdown = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", markdown)
        markdown = re.sub(r"<img[^>]*>", "", markdown)

        by_id, unassigned = self._image_markdown(draft, platform)
        if not by_id and not unassigned:
            return markdown

        used_ids: set[str] = set()

        def _replace_placeholder(match: re.Match[str]) -> str:
            image_id = match.group(1).strip()
            image_md = by_id.get(image_id)
            if not image_md:
                return ""
            used_ids.add(image_id)
            return image_md

        merged = self.IMAGE_PLACEHOLDER_PATTERN.sub(_replace_placeholder, markdown)
        merged = re.sub(r"\n{3,}", "\n\n", merged).strip() + "\n"

        remaining = unassigned + [img for image_id, img in by_id.items() if image_id not in used_ids]
        if remaining:
            ref_match = re.search(r"\n##\s+参考资料\s*\n", merged)
            if ref_match:
                insert_at = ref_match.start()
                prefix = merged[:insert_at].rstrip() + "\n\n" + "\n\n".join(remaining) + "\n\n"
                merged = prefix + merged[insert_at:].lstrip("\n")
            else:
                merged = merged.rstrip() + "\n\n" + "\n\n".join(remaining) + "\n"
            return merged

        return merged

    def _cleanup_for_publish(self, markdown: str) -> str:
        markdown = self._strip_outer_code_fence(markdown)
        markdown = re.sub(r"<!--\s*IMAGE_PROMPT\s*\{[\s\S]*?\}\s*-->", "", markdown)
        blocked_sections = {
            "元老院方案",
            "元老院质控意见",
            "调研关键要点",
            "Hexo 与知乎的平台适配要点",
            "落地建议与下一步",
        }
        mock_markers = (
            "[MOCK RESPONSE]",
            "System prompt intent:",
            "Generated text is deterministic placeholder content",
            "User request:",
            "Model:",
            "> 写作构思：",
        )

        lines = markdown.splitlines()
        kept: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Never keep markdown fence wrappers in publish output.
            if stripped.startswith("```"):
                i += 1
                continue

            if any(marker.lower() in stripped.lower() for marker in mock_markers):
                i += 1
                continue

            if stripped.startswith("## "):
                heading = stripped[3:].strip()
                if heading in blocked_sections:
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith("## "):
                        i += 1
                    continue

            kept.append(line)
            i += 1

        cleaned = "\n".join(kept)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"
        return cleaned

    def to_hexo(self, draft: DraftPackage) -> PlatformArticle:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        front_matter = "\n".join(
            [
                "---",
                f"title: \"{draft.title}\"",
                f"date: {date}",
                "tags:",
                "  - AI",
                "  - Agent",
                "  - Automation",
                "categories:",
                "  - Engineering",
                "---",
                "",
            ]
        )
        return PlatformArticle(
            platform="hexo",
            title=draft.title,
            markdown=front_matter + self._inject_images_into_markdown(self._cleanup_for_publish(draft.markdown), draft, "hexo"),
        )

    def to_zhihu(self, draft: DraftPackage) -> PlatformArticle:
        intro = (
            "在内容生产中，真正稀缺的不是写作本身，而是高质量调研和结构化表达。"
            "下面这套流程可以把一个想法快速变成可发布文章。\n\n"
        )
        body = self._cleanup_for_publish(draft.markdown)
        body = body.replace("## TL;DR", "## 一句话结论")
        body = body.replace("## References", "## 参考资料")
        body = re.sub(r"^#\s+.+\n+", "", body, count=1)
        body = self._inject_images_into_markdown(body, draft, "zhihu")
        return PlatformArticle(
            platform="zhihu",
            title=draft.title,
            markdown=f"# {draft.title}\n\n{intro}{body}",
        )

    def publish_variants(self, draft: DraftPackage) -> list[PlatformArticle]:
        return [self.to_hexo(draft), self.to_zhihu(draft)]
