import sys
import unittest
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget
from App_Gui import MainWindow

class TestAppGui(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_main_window_creation_and_file_list_exists(self):
        main_window = MainWindow()
        self.assertIsNotNone(main_window, "Main window should not be None")
        self.assertIsInstance(main_window, QMainWindow, "Main window should be an instance of QMainWindow")

        # Access the list widget, assuming it's named self.list_widget in MainWindow
        list_widget = getattr(main_window, 'list_widget', None)

        self.assertIsNotNone(list_widget, "QListWidget instance variable 'list_widget' should exist in MainWindow")
        self.assertIsInstance(list_widget, QListWidget, "list_widget should be an instance of QListWidget")

    # Example of how you might tear down the application if needed,
    # though for simple tests like this, it might not be strictly necessary.
    # @classmethod
    # def tearDownClass(cls):
    #     if cls.app:
    #         cls.app.quit() # Ensures the Qt event loop is terminated

if __name__ == "__main__":
    unittest.main()
