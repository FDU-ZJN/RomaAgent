from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _resolve_app_path() -> Path:
    # PyInstaller onefile extracts files to _MEIPASS.
    if hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
        candidate = base / "python-ui" / "app.py"
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent / "app.py"


def _parse_cli_port(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-p", "--port", type=int)
    args, _ = parser.parse_known_args(argv)

    if args.port is None:
        return int(os.environ.get("STREAMLIT_SERVER_PORT", "8501"))
    if not 1 <= args.port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")
    return args.port


def main() -> None:
    app_path = _resolve_app_path()
    if not app_path.exists():
        raise FileNotFoundError(f"Cannot locate Streamlit app file: {app_path}")

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
    # developmentMode=True conflicts with server.port override in Streamlit.
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    port = _parse_cli_port(sys.argv[1:])
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)

    flag_options = {
        # Use CLI-style option names expected by streamlit.web.cli/_main_run.
        "global_developmentMode": False,
        "server_headless": True,
        "server_port": port,
        "server_address": os.environ.get("STREAMLIT_SERVER_ADDRESS", "127.0.0.1"),
        "browser_gatherUsageStats": False,
    }

    # Prefer Streamlit's CLI codepath so options are loaded exactly like `streamlit run`.
    try:
        from streamlit.web.cli import _main_run

        _main_run(str(app_path), args=[], flag_options=flag_options)
    except Exception:
        from streamlit.web.bootstrap import load_config_options, run

        load_config_options(flag_options=flag_options)
        run(str(app_path), False, [], flag_options)


if __name__ == "__main__":
    main()
