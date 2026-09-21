"""Pytest configuration for tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to sys.path so we can import scripts
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
