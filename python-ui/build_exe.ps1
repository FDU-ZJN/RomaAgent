$ErrorActionPreference = 'Stop'

Write-Host '[1/4] Remove stale editable .pth if exists...'
Get-ChildItem "D:\anaconda3\envs\roma-agent\Lib\site-packages\__editable__.roma_agent*.pth" -ErrorAction SilentlyContinue |
	ForEach-Object { Remove-Item $_.FullName -Force }

Write-Host '[2/4] Install packaging dependency (PyInstaller)...'
cmd /c "call conda activate roma-agent & python -m pip install --upgrade pyinstaller"

Write-Host '[3/4] Install project package for build (non-editable)...'
cmd /c "call conda activate roma-agent & python -m pip install --force-reinstall ."

Write-Host '[4/4] Build executable with spec...'
cmd /c "call conda activate roma-agent & pyinstaller --noconfirm --clean .\python-ui\roma_agent_ui.spec"
Write-Host '[Done] Output: .\dist\RomaAgentPythonUI.exe'
