"""
Pytest configuration for backend test suite.
Ensures both backend directory and repository root are on sys.path.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(1, str(REPO_ROOT))
