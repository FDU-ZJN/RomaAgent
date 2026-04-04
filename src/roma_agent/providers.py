from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable

import requests

from .models import ImageAsset


class LLMProvider:
    """Simple provider interface used by the pipeline."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        raise NotImplementedError


class ImageProvider:
    def generate_image(self, prompt: str, output_dir: Path, name_prefix: str, alt_text: str) -> ImageAsset:
        raise NotImplementedError


@dataclass
class MockProvider(LLMProvider):
    model: str = "mock-model"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        text = (
            "[MOCK RESPONSE]\n"
            f"Model: {self.model}\n"
            f"System prompt intent: {system_prompt[:120]}\n"
            "Generated text is deterministic placeholder content so you can test the full pipeline.\n\n"
            f"User request:\n{user_prompt}\n"
        )
        if on_chunk is not None:
            for idx in range(0, len(text), 24):
                on_chunk(text[idx : idx + 24])
        return text


@dataclass
class AgentFrameworkProvider(LLMProvider):
    model: str

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        if find_spec("agent_framework") is None:
            raise RuntimeError(
                "agent-framework is not installed. Install dependencies first."
            )

        runtime = os.getenv("ROMA_AGENT_RUNTIME", "auto").strip().lower()
        custom_openai_base = os.getenv("OPENAI_BASE_URL", "").strip()
        errors: list[str] = []

        if runtime in {"auto", "foundry"}:
            try:
                return self._generate_with_foundry(system_prompt, user_prompt, on_chunk)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"foundry runtime failed: {exc}")

        if runtime in {"auto", "openai"}:
            # For OpenAI-compatible gateways (non-official endpoints), REST is
            # typically more stable than AF OpenAI surfaces across versions.
            if custom_openai_base and "api.openai.com" not in custom_openai_base:
                try:
                    return self._generate_with_openai_rest(system_prompt, user_prompt, on_chunk)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"openai-compatible REST failed: {exc}")
            else:
                try:
                    return self._generate_with_openai_agent_framework(system_prompt, user_prompt, on_chunk)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"openai runtime via Agent Framework failed: {exc}")

                try:
                    return self._generate_with_openai_rest(system_prompt, user_prompt, on_chunk)
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"openai REST fallback failed: {exc}")

        detail = " | ".join(errors) if errors else "no runtime attempted"
        if any("empty message content" in item.lower() for item in errors):
            # Allow downstream role-specific fallbacks to continue the pipeline.
            return ""
        raise RuntimeError(
            "AgentFrameworkProvider could not generate output. "
            "Set ROMA_AGENT_RUNTIME to foundry/openai/auto and provide required credentials. "
            f"Details: {detail}"
        )

    def _generate_with_foundry(
        self,
        system_prompt: str,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None,
    ) -> str:
        from importlib import import_module

        endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "").strip() or os.getenv(
            "AZURE_AI_PROJECT_ENDPOINT", ""
        ).strip()
        deployment = os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "").strip() or os.getenv(
            "AZURE_AI_MODEL_DEPLOYMENT_NAME", ""
        ).strip() or self.model

        if not endpoint:
            raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT/AZURE_AI_PROJECT_ENDPOINT is required for foundry runtime.")

        af_module = import_module("agent_framework")
        foundry_module = import_module("agent_framework.foundry")
        Agent = getattr(af_module, "Agent", None)
        if Agent is None:
            raise RuntimeError("agent_framework.Agent is not available in installed version.")

        client_cls = getattr(foundry_module, "FoundryChatClient", None)
        if client_cls is None:
            raise RuntimeError("FoundryChatClient is not available in installed agent_framework package.")

        credential = self._build_azure_credential_if_available()

        constructor_variants: list[dict[str, Any]] = [
            {"project_endpoint": endpoint, "model": deployment, "credential": credential},
            {"project_endpoint": endpoint, "model": deployment},
            {"model": deployment, "credential": credential},
            {"model": deployment},
            {},
        ]

        last_error: Exception | None = None
        client = None
        for kwargs in constructor_variants:
            kwargs = {k: v for k, v in kwargs.items() if v is not None}
            try:
                client = client_cls(**kwargs)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        if client is None:
            raise RuntimeError(f"Failed to construct FoundryChatClient: {last_error}")

        agent = Agent(
            client=client,
            name="RomaAFProvider",
            instructions=system_prompt,
        )
        return self._run_agent(agent, user_prompt, on_chunk)

    def _generate_with_openai_agent_framework(
        self,
        system_prompt: str,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None,
    ) -> str:
        from importlib import import_module

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for openai runtime.")

        af_module = import_module("agent_framework")
        openai_module = import_module("agent_framework.openai")
        Agent = getattr(af_module, "Agent", None)
        if Agent is None:
            raise RuntimeError("agent_framework.Agent is not available in installed version.")

        client_cls = getattr(openai_module, "OpenAIChatClient", None)
        if client_cls is None:
            client_cls = getattr(openai_module, "OpenAIChatCompletionClient", None)
        if client_cls is None:
            raise RuntimeError("OpenAI client class not found in agent_framework.openai.")

        constructor_variants: list[dict[str, Any]] = [
            {"api_key": api_key, "model": self.model},
            {"model": self.model},
            {},
        ]
        last_error: Exception | None = None
        client = None
        for kwargs in constructor_variants:
            try:
                client = client_cls(**kwargs)
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        if client is None:
            raise RuntimeError(f"Failed to construct Agent Framework OpenAI client: {last_error}")

        agent = Agent(
            client=client,
            name="RomaAFProvider",
            instructions=system_prompt,
        )
        return self._run_agent(agent, user_prompt, on_chunk)

    def _generate_with_openai_rest(
        self,
        system_prompt: str,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None,
    ) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for REST fallback.")
        timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))
        max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
        base_backoff = float(os.getenv("OPENAI_RETRY_BACKOFF_SECONDS", "1.5"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))
        thinking_type = os.getenv("OPENAI_THINKING_TYPE", "disabled").strip().lower()

        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        if base_url:
            normalized = base_url.rstrip("/")
            if normalized.endswith("/chat/completions"):
                endpoint = normalized
            else:
                endpoint = normalized + "/chat/completions"
        else:
            endpoint = "https://api.openai.com/v1/chat/completions"

        last_error: Exception | None = None
        response = None
        use_stream = on_chunk is not None
        for attempt in range(max_retries + 1):
            try:
                payload: dict[str, Any] = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": max_tokens,
                }
                if use_stream:
                    payload["stream"] = True
                if thinking_type in {"enabled", "disabled", "auto"}:
                    payload["thinking"] = {"type": thinking_type}

                response = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=timeout_seconds,
                    stream=use_stream,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < max_retries:
                        time.sleep(base_backoff * (2**attempt))
                        continue
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt < max_retries:
                    time.sleep(base_backoff * (2**attempt))
                    continue
                raise RuntimeError(f"OpenAI-compatible REST request failed after retries: {exc}") from exc

        if response is None:
            raise RuntimeError(f"OpenAI-compatible REST request failed: {last_error}")

        if use_stream:
            chunks: list[str] = []
            # Some OpenAI-compatible gateways may omit charset in SSE headers.
            # Decode bytes explicitly as UTF-8 to avoid mojibake.
            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="replace").strip()
                else:
                    line = str(raw_line).strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except Exception:
                    continue
                choices = event.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                text = delta.get("content")
                if not text and isinstance(choices[0].get("message", {}).get("content"), str):
                    text = choices[0].get("message", {}).get("content")
                if isinstance(text, str) and text:
                    chunks.append(text)
                    on_chunk(text)

            final_text = "".join(chunks).strip()
            if not final_text:
                raise RuntimeError("OpenAI REST stream returned empty message content.")
            return final_text

        payload = response.json()
        choices = payload.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI REST returned no choices.")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if (not isinstance(content, str) or not content.strip()) and isinstance(message.get("reasoning_content"), str):
            content = message.get("reasoning_content", "")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI REST returned empty message content.")
        return content.strip()

    def _run_agent(
        self,
        agent: Any,
        user_prompt: str,
        on_chunk: Callable[[str], None] | None,
    ) -> str:
        if hasattr(agent, "run"):
            maybe_coro = agent.run(user_prompt)
        elif hasattr(agent, "RunAsync"):
            maybe_coro = agent.RunAsync(user_prompt)
        else:
            raise RuntimeError("Agent object does not expose run/RunAsync methods.")

        if asyncio.iscoroutine(maybe_coro):
            result = self._run_coroutine(maybe_coro)
        else:
            result = maybe_coro
        text = str(result).strip()
        if on_chunk is not None and text:
            on_chunk(text)
        return text

    def _run_coroutine(self, coro: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        # If we are already inside an event loop, execute in a separate thread.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(coro))
            return future.result()

    def _build_azure_credential_if_available(self) -> Any:
        if find_spec("azure.identity") is None:
            return None
        try:
            from importlib import import_module

            azure_identity = import_module("azure.identity")
            AzureCliCredential = getattr(azure_identity, "AzureCliCredential", None)
            if AzureCliCredential is None:
                return None
            return AzureCliCredential()
        except Exception:  # noqa: BLE001
            return None


def build_provider(provider_name: str, model: str) -> LLMProvider:
    normalized = provider_name.strip().lower()
    if normalized == "mock":
        return MockProvider(model=model)
    if normalized in {"agent_framework", "agent-framework", "af"}:
        return AgentFrameworkProvider(model=model)
    raise ValueError(f"Unsupported provider: {provider_name}")


@dataclass
class OpenAICompatibleImageProvider(ImageProvider):
    model: str
    size: str = "1024x1024"

    def generate_image(self, prompt: str, output_dir: Path, name_prefix: str, alt_text: str) -> ImageAsset:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            return ImageAsset(alt_text=alt_text, prompt=prompt, status="skipped_no_api_key")

        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        if base_url:
            endpoint = base_url.rstrip("/") + "/images/generations"
        else:
            endpoint = "https://api.openai.com/v1/images/generations"

        if self._is_modelscope_endpoint(endpoint):
            return self._generate_with_modelscope_async(
                endpoint=endpoint,
                api_key=api_key,
                prompt=prompt,
                output_dir=output_dir,
                name_prefix=name_prefix,
                alt_text=alt_text,
            )

        timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": self.size,
            "response_format": "b64_json",
        }
        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            raise RuntimeError("Image generation returned empty data.")

        item = data[0]
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{name_prefix}.png"
        file_path = output_dir / filename

        if isinstance(item.get("b64_json"), str) and item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
            file_path.write_bytes(raw)
            relative = f"images/{filename}"
            return ImageAsset(
                alt_text=alt_text,
                prompt=prompt,
                relative_path=relative,
                status="generated",
            )

        if isinstance(item.get("url"), str) and item.get("url"):
            return ImageAsset(
                alt_text=alt_text,
                prompt=prompt,
                source_url=item["url"],
                status="generated",
            )

        raise RuntimeError("Image generation returned unsupported payload.")

    def _is_modelscope_endpoint(self, endpoint: str) -> bool:
        return "modelscope.cn" in endpoint.lower()

    def _generate_with_modelscope_async(
        self,
        endpoint: str,
        api_key: str,
        prompt: str,
        output_dir: Path,
        name_prefix: str,
        alt_text: str,
    ) -> ImageAsset:
        timeout_seconds = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "90"))
        poll_interval = float(os.getenv("ROMA_IMAGE_POLL_INTERVAL_SECONDS", "3"))
        poll_timeout = int(os.getenv("ROMA_IMAGE_POLL_TIMEOUT_SECONDS", "180"))

        submit_payload = {
            "model": self.model,
            "prompt": prompt,
        }
        submit_resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-ModelScope-Async-Mode": "true",
            },
            data=json.dumps(submit_payload, ensure_ascii=False).encode("utf-8"),
            timeout=timeout_seconds,
        )
        submit_resp.raise_for_status()
        submit_json = submit_resp.json()
        task_id = submit_json.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise RuntimeError(f"ModelScope image task_id missing: {submit_json}")

        base = endpoint.rsplit("/images/generations", 1)[0]
        if not base.endswith("/v1"):
            base = base.rstrip("/") + "/v1"
        task_endpoint = f"{base}/tasks/{task_id}"

        started_at = time.time()
        while time.time() - started_at < poll_timeout:
            task_resp = requests.get(
                task_endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-ModelScope-Task-Type": "image_generation",
                },
                timeout=timeout_seconds,
            )
            task_resp.raise_for_status()
            task_json = task_resp.json()
            status = str(task_json.get("task_status", "")).upper()

            if status == "SUCCEED":
                output_images = task_json.get("output_images", [])
                if not output_images:
                    raise RuntimeError(f"ModelScope image task succeeded but no output_images: {task_json}")
                image_url = output_images[0]

                image_resp = requests.get(image_url, timeout=timeout_seconds)
                image_resp.raise_for_status()
                output_dir.mkdir(parents=True, exist_ok=True)
                filename = f"{name_prefix}.png"
                file_path = output_dir / filename
                file_path.write_bytes(image_resp.content)

                return ImageAsset(
                    alt_text=alt_text,
                    prompt=prompt,
                    relative_path=f"images/{filename}",
                    source_url=image_url,
                    status="generated",
                )

            if status == "FAILED":
                message = task_json.get("message") or task_json.get("error") or task_json
                raise RuntimeError(f"ModelScope image task failed: {message}")

            time.sleep(max(0.5, poll_interval))

        raise RuntimeError(f"ModelScope image task polling timeout after {poll_timeout}s")


def build_image_provider(provider_name: str, image_model: str, image_size: str) -> ImageProvider:
    normalized = provider_name.strip().lower()
    if normalized in {"agent_framework", "agent-framework", "af"}:
        return OpenAICompatibleImageProvider(model=image_model, size=image_size)
    if normalized == "mock":
        return OpenAICompatibleImageProvider(model=image_model, size=image_size)
    raise ValueError(f"Unsupported provider for image generation: {provider_name}")

