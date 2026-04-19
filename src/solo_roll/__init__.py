from pathlib import Path

__version__ = "0.1.0"

_PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = _PACKAGE_DIR.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data"
