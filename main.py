import sys

from PyQt5.QtWidgets import QApplication

from gui import SimpleColumnAssist


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SimpleColumnAssist()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

