# Drive Cleaner (Offline)

Drive Cleaner is a local-first Python desktop app for Windows that:
- Scans C:/ and calculates folder and subfolder sizes
- Stores scan results in a local SQLite database
- Shows top disk usage with bar or pie charts
- Lets you choose cleanup categories (temp, cache, duplicate downloads, junk)
- Always previews cleanup candidates before deletion
- Blocks protected system paths and critical file types
- Moves files to Recycle Bin by default

## Requirements
- Python 3.11+
- Windows

Install:

python -m pip install -r requirements.txt

## Run

python -m cleaner

or

python run.py

## Project Modules
- cleaner/scanning: scan engine, file classification, duplicate detection
- cleaner/storage: SQLite schema and queries
- cleaner/visualization: matplotlib chart generation
- cleaner/cleanup: safety policy, preview, recycle-bin execution
- cleaner/gui: Tkinter UI

## Safety Model
- Protected roots include Windows, Program Files, ProgramData, Recovery, and system metadata folders.
- Protected file types include exe, dll, sys, msi, drv.
- Every cleanup operation requires preview first.
- Deletion path uses Recycle Bin (not permanent delete).

## Extend Later
- Add more category rules in cleaner/scanning/classifier.py
- Add new safety constraints in cleaner/cleanup/safety.py
- Add reports and additional chart views in cleaner/visualization/charts.py
