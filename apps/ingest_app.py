from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui_ingest.ingest_window import IngestWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = IngestWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
