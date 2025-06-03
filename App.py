import sys
from PyQt6.QtWidgets import QApplication
from App_Gui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
