from pathlib import Path

__version__ = "0.1.0"

# __file__ = src/solo_roll/__init__.py
# .parent  = src/solo_roll/
# .parent  = src/
# .parent  = repo root  (where data/ lives)
_PACKAGE_DIR = Path(__file__).resolve().parent   # src/solo_roll/
REPO_ROOT = _PACKAGE_DIR.parent.parent           # src/ → repo root
DEFAULT_DATA_DIR = REPO_ROOT / "data"
OSE_DATA_DIR = REPO_ROOT / "templates" / "ose" / "data"
