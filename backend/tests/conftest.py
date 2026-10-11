"""
Pytest configuration for backend/tests.
Ensures sys.path includes backend and root directories regardless of execution directory.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(1, str(REPO_ROOT))
