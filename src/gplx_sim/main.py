from __future__ import annotations

import sys
from importlib.resources import files

from PySide6.QtWidgets import QApplication, QMessageBox

from gplx_sim.bootstrap import initialize_databases
from gplx_sim.paths import AppPaths
from gplx_sim.repositories.content_repository import ContentRepository
from gplx_sim.repositories.history_repository import HistoryRepository
from gplx_sim.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Mô phỏng GPLX")
    application.setOrganizationName("MoPhongGPLX")
    stylesheet = files("gplx_sim.resources").joinpath("app.qss").read_text(encoding="utf-8")
    application.setStyleSheet(stylesheet)

    paths = AppPaths.discover()
    try:
        initialize_databases(paths)
    except OSError as error:
        QMessageBox.critical(None, "Không thể khởi tạo", f"Không thể tạo dữ liệu ứng dụng:\n{error}")
        return 1

    window = MainWindow(
        ContentRepository(paths.content_database),
        HistoryRepository(paths.history_database),
        paths.videos_directory,
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

