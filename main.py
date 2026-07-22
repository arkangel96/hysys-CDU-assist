import sys

from PyQt5.QtWidgets import QApplication

from gui import CduAssist


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = CduAssist()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
