@echo off
uv run pytest --cov --cov-report=term-missing --cov-report=html
echo.
echo Coverage report generated in htmlcov\index.html
