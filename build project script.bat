@echo off
cd %~dp0
pyinstaller --onefile --noconsole word_counter.py
pause