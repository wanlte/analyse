import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["APP_DB"] = str(Path(_tmp) / "app.db")
os.environ["DATA_ROOT"] = str(Path(_tmp) / "data")
