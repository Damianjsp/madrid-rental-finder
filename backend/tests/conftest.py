from pathlib import Path
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
