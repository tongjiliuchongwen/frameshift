@echo off
chcp 65001 >nul
title reframe-ui channel
cd /d "%~dp0"
REM Runs base = <repo>\test-runs ; the channel auto-picks the newest run there.
set "REFRAME_BASE=%~dp0..\..\test-runs"
echo.
echo   Starting Claude Code with the reframe-ui click-UI channel...
echo   Runs base : %REFRAME_BASE%
echo.
echo   Next:  1) approve the dev-channel prompt
echo          2) open  http://localhost:8765  in your browser
echo          3) click the gates; selections land in this session
echo.
claude --dangerously-load-development-channels server:reframe-ui
echo.
echo   (Claude Code exited. You can close this window.)
pause >nul
