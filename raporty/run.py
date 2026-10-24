"""Punkt startowy: python raporty/run.py --user-id 1 --granularity month --format json"""
import os
import sys

app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(app_root, "libs"))
sys.path.insert(0, app_root)

from raporty.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
