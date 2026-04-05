from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceNote:
    title: str
    url: str
    summary: str
    confidence: float = 0.5


@dataclass
class ResearchPackage:
    idea: str
    search_queries: list[str] = field(default_factory=list)
    notes: list[SourceNote] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)


@dataclass
class DraftPackage:
    title: str
    outline: list[str]
    markdown: str
    citations: list[str] = field(default_factory=list)
    image_plan: list[str] = field(default_factory=list)
    image_prompt_specs: list["ImagePromptSpec"] = field(default_factory=list)
    images: list["ImageAsset"] = field(default_factory=list)


@dataclass
class ImagePromptSpec:
    heading: str
    image_id: str = ""
    section: str = ""
    alt_text: str = ""
    prompt: str = ""
    rationale: str = ""


@dataclass
class ImageAsset:
    alt_text: str
    prompt: str
    image_id: str = ""
    section: str = ""
    relative_path: str = ""
    source_url: str = ""
    status: str = "generated"


@dataclass
class PlatformArticle:
    platform: str
    title: str
    markdown: str


@dataclass
class DeploymentRecord:
    platform: str
    output_path: str
    status: str


@dataclass
class PipelineResult:
    run_id: str
    research: ResearchPackage
    senate_design: str
    consul_draft: DraftPackage
    senate_quality_score: float
    senate_quality_notes: list[str]
    senate_rework_rounds: int
    senate_rework_triggered: bool
    tribune_issues: list[str]
    draft: DraftPackage
    platform_articles: list[PlatformArticle]
    deployment_records: list[DeploymentRecord]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
