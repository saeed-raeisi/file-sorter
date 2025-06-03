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


class TestFileTypeScannerLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Sample files
        self.txt_file_path = os.path.join(self.test_dir, "sample.txt")
        with open(self.txt_file_path, "w") as f:
            f.write("This is a test text file.")

        self.empty_file_path = os.path.join(self.test_dir, "empty.dat")
        open(self.empty_file_path, 'a').close()

        self.html_file_path = os.path.join(self.test_dir, "sample.html")
        with open(self.html_file_path, "w") as f:
            f.write("<html><body><h1>Test</h1></body></html>")

        self.pdf_file_path = os.path.join(self.test_dir, "sample.pdf")
        with open(self.pdf_file_path, "wb") as f:
            f.write(b"%PDF-1.4\n%fake content to make it non-empty...") # Minimal PDF-like start

        # Directory to be scanned
        self.scan_target_dir = os.path.join(self.test_dir, "scan_area")
        os.makedirs(self.scan_target_dir)

        shutil.copy(self.txt_file_path, self.scan_target_dir)
        shutil.copy(self.empty_file_path, self.scan_target_dir)
        shutil.copy(self.html_file_path, self.scan_target_dir)
        shutil.copy(self.pdf_file_path, self.scan_target_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_identifies_known_file_types(self):
        progress_calls = []
        error_calls = []

        # Simple is_running_check, always true for direct calls.
        is_running_stub = lambda: True

        results = scan_files_core(
            [self.scan_target_dir],
            lambda m, p: progress_calls.append((m, p)),
            lambda m: error_calls.append(m),
            is_running_stub
        )

        self.assertEqual(len(error_calls), 0, f"Encountered errors during scan: {error_calls}")
        self.assertEqual(len(results), 4, f"Should have processed 4 files, found {len(results)} results: {results}")

        identified_types = {}
        for r in results:
            identified_types[r["filename"]] = r["identified_type"]

        self.assertIn("sample.txt", identified_types)
        self.assertTrue(identified_types["sample.txt"].startswith("text/plain"),
                        f"Expected text/plain for .txt, got {identified_types['sample.txt']}")

        self.assertIn("empty.dat", identified_types)
        # Empty file type can vary based on libmagic version and OS
        # Common types include 'inode/x-empty' and 'application/octet-stream'
        # Sometimes 'application/x-zerosize' or others.
        # For some libmagic versions, empty files can cause MagicException, handled in core logic.
        empty_type = identified_types["empty.dat"]
        self.assertTrue(
            empty_type in ["inode/x-empty", "application/octet-stream", "application/x-zerosize"] or "MagicError: empty file" in empty_type,
            f"Expected specific types or empty file error for empty.dat, got {empty_type}"
        )

        self.assertIn("sample.html", identified_types)
        self.assertTrue(identified_types["sample.html"].startswith("text/html"),
                        f"Expected text/html for .html, got {identified_types['sample.html']}")

        self.assertIn("sample.pdf", identified_types)
        # The sample PDF is very minimal. Some libmagic versions might identify it as application/pdf,
        # others might see it as text/plain or application/octet-stream due to lack of structure.
        pdf_type = identified_types["sample.pdf"]
        self.assertTrue(
            pdf_type.startswith("application/pdf") or \
            pdf_type.startswith("text/plain") or \
            pdf_type.startswith("application/octet-stream") or \
            "MagicError" in pdf_type, # If libmagic has issues with the minimal content
            f"Expected application/pdf, text/plain, or octet-stream for minimal .pdf, got {pdf_type}"
        )

    def test_scan_empty_directory_for_types(self):
        empty_scan_dir = os.path.join(self.test_dir, "empty_for_type_scan")
        os.makedirs(empty_scan_dir)
        results = scan_files_core([empty_scan_dir], lambda m, p: None, lambda m: None, lambda: True)
        self.assertEqual(len(results), 0)

    def test_error_callback_for_nonexistent_dir(self):
        error_calls = []
        non_existent_path = os.path.join(self.test_dir, "nonexistent_dir123")
        scan_files_core([non_existent_path], lambda m, p: None, lambda m: error_calls.append(m), lambda: True)

        self.assertTrue(len(error_calls) > 0, "Error callback was not called for a non-existent directory.")
        # Check if any of the error messages contain the expected substring
        self.assertTrue(
            any("Directory not found" in call and non_existent_path in call for call in error_calls),
            f"Expected error message for non-existent directory not found in {error_calls}"
        )
