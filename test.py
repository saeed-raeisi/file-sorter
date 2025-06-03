import sys
import unittest
import os
import shutil
import tempfile
import time # For progress/error callback timing if needed.
import threading # For the threading.Event in the QThread version, not needed for direct calls.

from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidget # Keep for TestAppGui
from App_Gui import MainWindow # Keep for TestAppGui

# Import the core logic function and the thread class (though tests for core will use the function directly)
from duplicate_finder_logic import find_duplicates_core, DuplicateScannerThread

# Ensure QT_QPA_PLATFORM is set for headless environments for TestAppGui
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestAppGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv if hasattr(sys, 'argv') else ['test'])

    def test_main_window_creation_and_file_list_exists(self):
        main_window = MainWindow()
        self.assertIsNotNone(main_window, "Main window should not be None")
        self.assertIsInstance(main_window, QMainWindow, "Main window should be an instance of QMainWindow")
        list_widget = getattr(main_window, 'list_widget', None)
        self.assertIsNotNone(list_widget, "QListWidget instance variable 'list_widget' should exist in MainWindow")
        self.assertIsInstance(list_widget, QListWidget, "list_widget should be an instance of QListWidget")

    # @classmethod
    # def tearDownClass(cls):
    #     pass # QApplication will clean up as tests end


class TestDuplicateFinderLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dir1 = os.path.join(self.test_dir, "dir1")
        self.dir2 = os.path.join(self.test_dir, "dir2")
        os.makedirs(self.dir1)
        os.makedirs(self.dir2)

        self.duplicate_content = b"duplicate content"
        self.unique_content1 = b"unique1"
        self.unique_content2 = b"unique2"
        self.empty_content = b""

        self.dup1_path = os.path.join(self.dir1, "dup1.txt")
        with open(self.dup1_path, "wb") as f: f.write(self.duplicate_content)

        self.dup2_path = os.path.join(self.dir2, "dup2.txt")
        with open(self.dup2_path, "wb") as f: f.write(self.duplicate_content)

        self.empty1_path = os.path.join(self.dir1, "empty1.txt") # For testing multiple duplicate sets
        with open(self.empty1_path, "wb") as f: f.write(self.empty_content)

        self.empty2_path = os.path.join(self.dir2, "empty2.txt")
        with open(self.empty2_path, "wb") as f: f.write(self.empty_content)

        self.unique1_path = os.path.join(self.dir1, "unique1.txt")
        with open(self.unique1_path, "wb") as f: f.write(self.unique_content1)

        self.unique2_path = os.path.join(self.dir2, "unique2.txt")
        with open(self.unique2_path, "wb") as f: f.write(self.unique_content2)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_finds_duplicates_across_dirs(self):
        # Test setup includes two pairs of duplicates:
        # 1. dup1.txt and dup2.txt (content: "duplicate content")
        # 2. empty1.txt and empty2.txt (content: "")
        results = find_duplicates_core([self.test_dir])

        self.assertEqual(len(results), 2, f"Expected 2 sets of duplicates, got {len(results)}. Results: {results}")

        # Normalize paths and sort for consistent comparison
        normalized_results = sorted([sorted([os.path.normpath(p) for p in group]) for group in results])

        expected_dup_set1 = sorted([os.path.normpath(self.dup1_path), os.path.normpath(self.dup2_path)])
        expected_empty_set = sorted([os.path.normpath(self.empty1_path), os.path.normpath(self.empty2_path)])

        self.assertIn(expected_dup_set1, normalized_results, "Content duplicate set not found or paths mismatched.")
        self.assertIn(expected_empty_set, normalized_results, "Empty file duplicate set not found or paths mismatched.")

    def test_no_duplicates_within_single_dir_with_unique_files(self):
        # dir1 contains dup1.txt, empty1.txt, and unique1.txt.
        # When scanned alone, no file within dir1 is a duplicate of another file *within dir1*.
        results = find_duplicates_core([self.dir1])
        self.assertEqual(len(results), 0, f"Found duplicates in dir1 when none expected: {results}")

    def test_scan_empty_directory(self):
        empty_subdir = os.path.join(self.test_dir, "empty_subdir")
        os.makedirs(empty_subdir)
        results = find_duplicates_core([empty_subdir])
        self.assertEqual(len(results), 0, f"Found duplicates in empty dir: {results}")

    def test_scan_multiple_unique_dirs(self):
        dir3 = os.path.join(self.test_dir, "dir3")
        os.makedirs(dir3)
        unique3_path = os.path.join(dir3, "unique3.txt")
        with open(unique3_path, "wb") as f: f.write(b"unique3_content")

        # dir1 contains: dup1.txt, empty1.txt, unique1.txt
        # dir3 contains: unique3.txt
        # No file in dir1 is a duplicate of a file in dir3, and no internal duplicates within these single dirs.
        results = find_duplicates_core([self.dir1, dir3])
        self.assertEqual(len(results), 0, f"Found duplicates when scanning multiple dirs with no cross-duplicates: {results}")

    def test_progress_and_error_callbacks(self):
        progress_calls = []
        error_calls = []

        def mock_progress(message, percentage):
            progress_calls.append((message, percentage))

        def mock_error(message): # Renamed from error_callback to mock_error for clarity
            error_calls.append(message)

        # Test with a directory that has a few files to ensure progress is called
        # self.test_dir contains multiple files and subdirectories
        find_duplicates_core([self.test_dir], mock_progress, mock_error)

        self.assertTrue(len(progress_calls) > 0, "Progress callback was not called")

        # To test error_callback, we need a scenario that reliably triggers it.
        # Example: permission denied (hard to set up reliably) or non-existent primary directory.
        # The current find_duplicates_core might not call error_callback for a non-existent *initial* directory.
        # Let's test error callback from _calculate_hash by creating a file that can't be read (though this is tricky)
        # For now, ensure no errors were reported during a normal scan.
        self.assertEqual(len(error_calls), 0, f"Error callback was unexpectedly called: {error_calls}")

        # Test error callback for a non-existent directory if the core logic handles it
        # Note: os.walk on a non-existent path doesn't run the loop, so error might not be from there.
        # The current find_duplicates_core's top-level try-except for os.walk might catch this.
        error_calls.clear() # Clear previous error calls
        non_existent_dir = os.path.join(self.test_dir, "non_existent_dir")
        find_duplicates_core([non_existent_dir], mock_progress, mock_error)
        # Check if an error related to "non_existent_dir" was reported
        # The error message was changed in find_duplicates_core
        found_expected_error = any("Directory not found or not a directory" in call and non_existent_dir in call for call in error_calls)
        self.assertTrue(found_expected_error, f"Expected error for non-existent directory not found in error_calls: {error_calls}")


if __name__ == "__main__":
    unittest.main()
