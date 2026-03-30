$ErrorActionPreference = "Stop"

python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name DriveCleaner run.py

$desktop = [Environment]::GetFolderPath('Desktop')
Copy-Item -Path .\dist\DriveCleaner.exe -Destination (Join-Path $desktop 'DriveCleaner.exe') -Force

Write-Host "Desktop app created: $(Join-Path $desktop 'DriveCleaner.exe')"
