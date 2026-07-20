import sys

from PyQt5.QtWidgets import QApplication

from gui import HysysStudio


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = HysysStudio()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

