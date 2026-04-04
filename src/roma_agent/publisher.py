from __future__ import annotations

import re
from datetime import datetime

from .models import DraftPackage, PlatformArticle


class PublisherAgent:
    def _strip_outer_code_fence(self, markdown: str) -> str:
        text = markdown.strip()
        # Remove whole-document fenced wrapper like ```markdown ... ```
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                return "\n".join(lines[1:-1]).strip() + "\n"
        return markdown

    def _image_markdown(self, draft: DraftPackage, platform: str) -> tuple[dict[str, list[str]], list[str]]:
        by_heading: dict[str, list[str]] = {}
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
            match = re.search(r"架构解释配图：(.+)$", item.alt_text)
            if match:
                heading = match.group(1).strip()
                by_heading.setdefault(heading, []).append(md)
            else:
                unassigned.append(md)
        return by_heading, unassigned

    def _inject_images_into_markdown(self, markdown: str, draft: DraftPackage, platform: str) -> str:
        if not draft.images:
            return markdown

        by_heading, unassigned = self._image_markdown(draft, platform)
        if not by_heading and not unassigned:
            return markdown

        lines = markdown.splitlines()
        output: list[str] = []

        for line in lines:
            output.append(line)
            stripped = line.strip()
            if stripped.startswith("## "):
                heading = stripped[3:].strip()
                inserts = by_heading.pop(heading, [])
                if inserts:
                    output.append("")
                    for idx, image_md in enumerate(inserts):
                        output.append(image_md)
                        if idx != len(inserts) - 1:
                            output.append("")
                    output.append("")

        remaining = unassigned + [img for items in by_heading.values() for img in items]
        if remaining:
            merged = "\n".join(output)
            ref_match = re.search(r"\n##\s+参考资料\s*\n", merged)
            if ref_match:
                insert_at = ref_match.start()
                prefix = merged[:insert_at].rstrip() + "\n\n" + "\n\n".join(remaining) + "\n\n"
                merged = prefix + merged[insert_at:].lstrip("\n")
            else:
                merged = merged.rstrip() + "\n\n" + "\n\n".join(remaining) + "\n"
            return merged

        return "\n".join(output)

    def _cleanup_for_publish(self, markdown: str) -> str:
        markdown = self._strip_outer_code_fence(markdown)
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
