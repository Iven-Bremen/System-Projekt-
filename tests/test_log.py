import os
import sys
from pathlib import Path
from datetime import datetime as real_datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import Log


def test_make_log_path_uses_date_and_start_time_folders(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return real_datetime(2026, 8, 3, 14, 25, 30)

    monkeypatch.setattr(Log, "datetime", FrozenDateTime)

    path = Log.make_log_path("M", base_name="run.csv")

    assert path == os.path.join("logs", "2026-08-03", "14-25-30", "run.csv")
    assert os.path.exists(os.path.dirname(path))
