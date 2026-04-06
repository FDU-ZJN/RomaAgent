from __future__ import annotations

import json
import os
import sys
import threading
import time
from queue import Empty, Queue
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

# Prefer installed/bundled package first; fall back to local src in development.
try:
    from roma_agent.config import Settings
    from roma_agent.pipeline import RomaPipeline
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    SRC_PATH = PROJECT_ROOT / "src"
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from roma_agent.config import Settings
    from roma_agent.pipeline import RomaPipeline


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def list_run_ids(output_root: Path) -> list[str]:
    if not output_root.exists():
        return []
    run_ids = [item.name for item in output_root.iterdir() if item.is_dir() and item.name[:8].isdigit()]
    run_ids.sort(reverse=True)
    return run_ids


def render_run_artifacts(run_dir: Path, header_prefix: str = "") -> None:
    if not run_dir.exists():
        st.info(f"{header_prefix}运行目录不存在: {run_dir}")
        return

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader(f"{header_prefix}Hexo 最终稿")
        hexo_text = read_text_if_exists(run_dir / "deployments" / "hexo.md")
        if hexo_text:
            st.code(hexo_text, language="markdown")
        else:
            st.info("未找到 Hexo 稿件")

    with col_right:
        st.subheader(f"{header_prefix}知乎最终稿")
        zhihu_text = read_text_if_exists(run_dir / "deployments" / "zhihu.md")
        if zhihu_text:
            st.code(zhihu_text, language="markdown")
        else:
            st.info("未找到知乎稿件")

    st.subheader(f"{header_prefix}元老院资料包")
    senate_text = read_text_if_exists(run_dir / "senate_brief.md")
    if senate_text:
        st.code(senate_text, language="markdown")

    st.subheader(f"{header_prefix}保民官报告")
    tribune_text = read_text_if_exists(run_dir / "tribune_report.md")
    if tribune_text:
        st.code(tribune_text, language="markdown")

    st.subheader(f"{header_prefix}图片元数据")
    images_text = read_text_if_exists(run_dir / "images.json")
    if images_text:
        try:
            st.json(json.loads(images_text))
        except Exception:
            st.code(images_text, language="json")


def run_pipeline_in_worker(settings: Settings, idea_input: str, queue: Queue[tuple[str, str]], holder: dict[str, Any]) -> None:
    logs: list[str] = []

    def on_log(message: str) -> None:
        logs.append(message)
        queue.put(("log", message))

    try:
        pipeline = RomaPipeline(settings=settings, on_log=on_log)
        result = pipeline.run(idea_input)
        holder["result"] = result
        holder["logs"] = logs
        queue.put(("done", result.run_id))
    except Exception as exc:  # noqa: BLE001
        holder["error"] = str(exc)
        holder["logs"] = logs
        queue.put(("error", str(exc)))


def env_or_default(key: str, default: str) -> str:
    value = os.getenv(key, "").strip()
    return value if value else default


def bool_to_env(value: bool) -> str:
    return "true" if value else "false"


def build_idea_input(title: str, idea: str, viewpoint: str) -> str:
    return f"标题: {title.strip()}\n核心想法: {idea.strip()}\n观点主张: {viewpoint.strip()}"


def set_runtime_env_from_form(form_values: dict[str, Any]) -> None:
    mapping = {
        "ROMA_PROVIDER": form_values["provider"],
        "ROMA_AGENT_RUNTIME": form_values["runtime"],
        "ROMA_MODEL": form_values["model"],
        "OPENAI_BASE_URL": form_values["openai_base_url"],
        "OPENAI_API_KEY": form_values["openai_api_key"],
        "ROMA_SEARCH_PROVIDER": form_values["search_provider"],
        "TAVILY_API_KEY": form_values["tavily_api_key"],
        "ROMA_MAX_SOURCES": str(form_values["max_sources"]),
        "ROMA_OUTPUT_DIR": form_values["output_dir"],
        "ROMA_ENABLE_IMAGE_CONSUL": bool_to_env(form_values["enable_image_consul"]),
        "ROMA_IMAGE_MODEL": form_values["image_model"],
        "ROMA_IMAGE_COUNT": str(form_values["image_count"]),
        "ROMA_IMAGE_SIZE": form_values["image_size"],
        "ROMA_SENATE_REJECT_SCORE_THRESHOLD": str(form_values["reject_threshold"]),
        "ROMA_SENATE_MAX_REWORK_ROUNDS": str(form_values["max_rework_rounds"]),
        "ROMA_ARTICLE_MIN_WORDS": str(form_values["article_min_words"]),
        "ROMA_ARTICLE_MAX_WORDS": str(form_values["article_max_words"]),
    }

    for key, value in mapping.items():
        os.environ[key] = value


def main() -> None:
    load_dotenv(override=True)

    st.set_page_config(page_title="RomaAgent Python UI", layout="wide")
    st.title("RomaAgent Python UI")
    st.caption("直接调用 roma_agent pipeline（无子进程，实时日志流式刷新）")

    output_root = Path(env_or_default("ROMA_OUTPUT_DIR", "output"))
    with st.sidebar:
        st.header("运行历史")
        history_ids = list_run_ids(output_root)
        selected_history = st.selectbox("选择 Run ID", options=[""] + history_ids, index=0)
        show_history = st.button("加载历史")

    with st.form("roma_run_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("文章标题", value="AI芯片架构技术演进与产业格局")
            idea = st.text_input("核心想法", value="围绕GPU、NPU与异构计算，写一篇结构化技术分析")
        with col2:
            viewpoint = st.text_area("观点主张", value="算力架构创新与供应链博弈共同驱动下一代AI基础设施", height=96)

        st.subheader("模型与检索参数")
        m1, m2, m3 = st.columns(3)
        with m1:
            provider = st.text_input("ROMA_PROVIDER", value=env_or_default("ROMA_PROVIDER", "mock"))
            runtime = st.text_input("ROMA_AGENT_RUNTIME", value=env_or_default("ROMA_AGENT_RUNTIME", "auto"))
            model = st.text_input("ROMA_MODEL", value=env_or_default("ROMA_MODEL", "gpt-4o-mini"))
        with m2:
            openai_base_url = st.text_input("OPENAI_BASE_URL", value=env_or_default("OPENAI_BASE_URL", ""))
            openai_api_key = st.text_input("OPENAI_API_KEY", value=env_or_default("OPENAI_API_KEY", ""), type="password")
            search_provider = st.text_input("ROMA_SEARCH_PROVIDER", value=env_or_default("ROMA_SEARCH_PROVIDER", "tavily"))
        with m3:
            tavily_api_key = st.text_input("TAVILY_API_KEY", value=env_or_default("TAVILY_API_KEY", ""), type="password")
            max_sources = st.number_input("ROMA_MAX_SOURCES", min_value=1, max_value=30, value=int(env_or_default("ROMA_MAX_SOURCES", "8")))
            output_dir = st.text_input("ROMA_OUTPUT_DIR", value=env_or_default("ROMA_OUTPUT_DIR", "output"))

        st.subheader("质量与图片参数")
        q1, q2, q3 = st.columns(3)
        with q1:
            reject_threshold = st.number_input(
                "ROMA_SENATE_REJECT_SCORE_THRESHOLD",
                min_value=0.0,
                max_value=100.0,
                value=float(env_or_default("ROMA_SENATE_REJECT_SCORE_THRESHOLD", "80")),
                step=1.0,
            )
            max_rework_rounds = st.number_input(
                "ROMA_SENATE_MAX_REWORK_ROUNDS",
                min_value=0,
                max_value=10,
                value=int(env_or_default("ROMA_SENATE_MAX_REWORK_ROUNDS", "2")),
            )
        with q2:
            article_min_words = st.number_input(
                "ROMA_ARTICLE_MIN_WORDS",
                min_value=200,
                max_value=20000,
                value=int(env_or_default("ROMA_ARTICLE_MIN_WORDS", "1200")),
                step=100,
            )
            article_max_words = st.number_input(
                "ROMA_ARTICLE_MAX_WORDS",
                min_value=300,
                max_value=30000,
                value=int(env_or_default("ROMA_ARTICLE_MAX_WORDS", "1800")),
                step=100,
            )
        with q3:
            enable_image_consul = st.checkbox(
                "ROMA_ENABLE_IMAGE_CONSUL",
                value=env_or_default("ROMA_ENABLE_IMAGE_CONSUL", "false").lower() in {"1", "true", "yes", "on"},
            )
            image_model = st.text_input("ROMA_IMAGE_MODEL", value=env_or_default("ROMA_IMAGE_MODEL", "gpt-image-1"))
            image_count = st.number_input(
                "ROMA_IMAGE_COUNT",
                min_value=0,
                max_value=20,
                value=int(env_or_default("ROMA_IMAGE_COUNT", "2")),
            )
            image_size = st.text_input("ROMA_IMAGE_SIZE", value=env_or_default("ROMA_IMAGE_SIZE", "512x512"))

        submitted = st.form_submit_button("开始生成", type="primary")

    if not submitted:
        if show_history and selected_history:
            st.subheader(f"历史结果: {selected_history}")
            render_run_artifacts(output_root / selected_history, header_prefix="历史-")
        return

    if not title.strip() or not idea.strip():
        st.error("请至少填写文章标题和核心想法。")
        return

    form_values = {
        "provider": provider.strip(),
        "runtime": runtime.strip(),
        "model": model.strip(),
        "openai_base_url": openai_base_url.strip(),
        "openai_api_key": openai_api_key.strip(),
        "search_provider": search_provider.strip(),
        "tavily_api_key": tavily_api_key.strip(),
        "max_sources": int(max_sources),
        "output_dir": output_dir.strip(),
        "enable_image_consul": enable_image_consul,
        "image_model": image_model.strip(),
        "image_count": int(image_count),
        "image_size": image_size.strip(),
        "reject_threshold": float(reject_threshold),
        "max_rework_rounds": int(max_rework_rounds),
        "article_min_words": int(article_min_words),
        "article_max_words": int(article_max_words),
    }

    if form_values["article_min_words"] > form_values["article_max_words"]:
        st.error("最小字数不能大于最大字数。")
        return

    set_runtime_env_from_form(form_values)

    status_placeholder = st.empty()
    log_placeholder = st.empty()
    metric_placeholder = st.empty()

    status_placeholder.info("状态：运行中")
    metric_placeholder.write("Run ID: - | Senate score: - | Tribune issues: -")

    queue: Queue[tuple[str, str]] = Queue()
    holder: dict[str, Any] = {}

    settings = Settings.load()
    idea_input = build_idea_input(title, idea, viewpoint)
    worker = threading.Thread(
        target=run_pipeline_in_worker,
        args=(settings, idea_input, queue, holder),
        daemon=True,
    )
    worker.start()

    stream_logs: list[str] = []
    done = False
    failed = False
    while worker.is_alive() or not queue.empty():
        try:
            event, data = queue.get(timeout=0.15)
        except Empty:
            time.sleep(0.05)
            continue

        if event == "log":
            stream_logs.append(data)
            log_placeholder.code("\n".join(stream_logs), language="text")
        elif event == "done":
            done = True
        elif event == "error":
            failed = True

    worker.join(timeout=0.2)

    if failed or "error" in holder:
        status_placeholder.error(f"状态：失败 - {holder.get('error', '未知错误')}")
        if stream_logs:
            log_placeholder.code("\n".join(stream_logs), language="text")
        return

    result = holder.get("result")
    if result is None:
        status_placeholder.error("状态：失败 - 未获得结果")
        return

    if done:
        status_placeholder.success("状态：成功")

    metric_placeholder.write(
        f"Run ID: {result.run_id} | Senate score: {result.senate_quality_score:.2f} | Tribune issues: {len(result.tribune_issues)}"
    )

    if stream_logs:
        with st.expander("运行日志", expanded=True):
            st.code("\n".join(stream_logs), language="text")

    run_dir = Path(settings.output_dir) / result.run_id
    render_run_artifacts(run_dir)

    st.divider()
    st.subheader("历史结果")
    if selected_history:
        render_run_artifacts(output_root / selected_history, header_prefix="历史-")


if __name__ == "__main__":
    main()
