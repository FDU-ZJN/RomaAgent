from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from .models import SourceNote


class SearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceNote]:
        raise NotImplementedError


@dataclass
class TavilySearchClient(SearchClient):
    api_key: str

    def search(self, query: str, max_results: int = 5) -> list[SourceNote]:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": self.api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
                "include_images": False,
                "search_depth": "advanced",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("results", [])

        notes: list[SourceNote] = []
        for item in items:
            title = str(item.get("title", "Untitled result")).strip()
            url = str(item.get("url", "")).strip()
            summary = str(item.get("content", "")).strip()
            score_raw = item.get("score", 0.65)
            confidence = float(score_raw) if isinstance(score_raw, (int, float)) else 0.65
            if not url:
                continue
            notes.append(
                SourceNote(
                    title=title[:160],
                    url=url,
                    summary=summary[:600] if summary else "No summary returned.",
                    confidence=max(0.0, min(1.0, confidence)),
                )
            )
        return notes


@dataclass
class BingSearchClient(SearchClient):
    endpoint: str
    api_key: str

    def search(self, query: str, max_results: int = 5) -> list[SourceNote]:
        endpoint = self.endpoint.rstrip("/")
        response = requests.get(
            f"{endpoint}/v7.0/search",
            params={"q": query, "count": max_results, "textFormat": "Raw"},
            headers={"Ocp-Apim-Subscription-Key": self.api_key},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        values = payload.get("webPages", {}).get("value", [])

        notes: list[SourceNote] = []
        for item in values:
            title = str(item.get("name", "Untitled result")).strip()
            url = str(item.get("url", "")).strip()
            summary = str(item.get("snippet", "")).strip()
            if not url:
                continue
            notes.append(
                SourceNote(
                    title=title[:160],
                    url=url,
                    summary=summary[:600] if summary else "No summary returned.",
                    confidence=0.7,
                )
            )
        return notes


class NullSearchClient(SearchClient):
    def search(self, query: str, max_results: int = 5) -> list[SourceNote]:
        return []


def build_search_client(provider: str) -> SearchClient:
    normalized = provider.strip().lower()
    if normalized == "tavily":
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            return NullSearchClient()
        return TavilySearchClient(api_key=api_key)

    if normalized in {"bing", "bing_v7"}:
        endpoint = os.getenv("BING_SEARCH_V7_ENDPOINT", "").strip()
        api_key = os.getenv("BING_SEARCH_V7_KEY", "").strip()
        if not endpoint or not api_key:
            return NullSearchClient()
        return BingSearchClient(endpoint=endpoint, api_key=api_key)

    return NullSearchClient()
