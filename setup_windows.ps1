$ErrorActionPreference = 'Stop'
Write-Host 'XAITA-OT Windows setup'
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
$env:PYTHONPATH = "$PWD\src"
pytest -q
python scripts\smoke_test.py
Write-Host 'Setup complete. Start API with: python run_api.py'
