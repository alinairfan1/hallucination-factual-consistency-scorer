import sys
from pathlib import Path

# Add root directory to Python path so the top-level `scripts` package is importable
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
