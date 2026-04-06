# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

spec_path = Path(globals().get("SPEC", os.path.join(os.getcwd(), "python-ui", "roma_agent_ui.spec"))).resolve()
project_root = spec_path.parent.parent

hiddenimports = [
    "streamlit.web.bootstrap",
    "streamlit.web.server.server",
    "streamlit.runtime.runtime",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "agent_framework",
    "agent_framework.openai",
    "agent_framework.foundry",
]
hiddenimports += collect_submodules("streamlit.runtime.scriptrunner")
hiddenimports += collect_submodules("agent_framework")
hiddenimports += collect_submodules("roma_agent")

# Include UI script and dotenv templates for runtime consistency.
datas = []
datas += collect_data_files("streamlit")
datas += collect_data_files("roma_agent")
datas += collect_data_files("agent_framework")
datas += copy_metadata("streamlit")
datas += copy_metadata("agent-framework")
datas.append((str(project_root / "python-ui" / "app.py"), "python-ui"))
if (project_root / ".env.example").exists():
    datas.append((str(project_root / ".env.example"), "."))

block_cipher = None

a = Analysis(
    [str(project_root / "python-ui" / "launcher.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "streamlit.external.langchain",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="RomaAgentPythonUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
