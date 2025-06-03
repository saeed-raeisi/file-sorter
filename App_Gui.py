import sys
import os
import time # For formatting date
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QListWidget, QHBoxLayout,
                             QLineEdit, QPushButton, QTabWidget, QFileDialog,
                             QTreeWidget, QTreeWidgetItem, QLabel, QMessageBox,
                             QTreeWidgetItemIterator)
from PyQt6.QtCore import Qt
from duplicate_finder_logic import DuplicateScannerThread
from file_type_scanner_logic import FileTypeScannerThread

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Manager")
        self.current_path = os.path.expanduser("~") # Used by File Browser
        self.sort_criteria = "name"  # Used by File Browser
        self.sort_reverse = False    # Used by File Browser
        self.dup_scanner_thread = None

        # Main Tab Widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # --- File Browser Tab ---
        file_browser_widget = QWidget()
        self.file_browser_layout = QVBoxLayout(file_browser_widget)

        nav_layout = QHBoxLayout()
        self.address_bar = QLineEdit()
        self.address_bar.setText(self.current_path)
        self.address_bar.returnPressed.connect(self.change_directory_from_address_bar)
        nav_layout.addWidget(self.address_bar)

        up_button = QPushButton("Up")
        up_button.clicked.connect(self.go_up_directory)
        nav_layout.addWidget(up_button)
        self.file_browser_layout.addLayout(nav_layout)

        sort_layout = QHBoxLayout()
        self.sort_name_button = QPushButton("Sort by Name")
        self.sort_name_button.clicked.connect(lambda: self.set_sort_criteria("name"))
        sort_layout.addWidget(self.sort_name_button)

        self.sort_date_button = QPushButton("Sort by Date")
        self.sort_date_button.clicked.connect(lambda: self.set_sort_criteria("date"))
        sort_layout.addWidget(self.sort_date_button)

        self.sort_type_button = QPushButton("Sort by Type")
        self.sort_type_button.clicked.connect(lambda: self.set_sort_criteria("type"))
        sort_layout.addWidget(self.sort_type_button)
        self.file_browser_layout.addLayout(sort_layout)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.handle_item_double_click)
        self.file_browser_layout.addWidget(self.list_widget)

        self.tab_widget.addTab(file_browser_widget, "File Browser")
        self.load_directory_contents(self.current_path)

        # --- Duplicate Finder Tab ---
        duplicate_finder_widget = QWidget()
        duplicate_finder_layout = QVBoxLayout(duplicate_finder_widget)

        dup_dir_label = QLabel("Folders to Scan:")
        duplicate_finder_layout.addWidget(dup_dir_label)

        self.dup_scan_paths_list = QListWidget()
        self.dup_scan_paths_list.model().rowsInserted.connect(self.update_dup_scan_button_state)
        self.dup_scan_paths_list.model().rowsRemoved.connect(self.update_dup_scan_button_state)
        duplicate_finder_layout.addWidget(self.dup_scan_paths_list)

        dup_buttons_layout = QHBoxLayout()
        self.dup_add_folder_button = QPushButton("Add Folder")
        self.dup_add_folder_button.clicked.connect(self.add_scan_folder)
        dup_buttons_layout.addWidget(self.dup_add_folder_button)

        self.dup_remove_folder_button = QPushButton("Remove Folder")
        self.dup_remove_folder_button.clicked.connect(self.remove_scan_folder)
        dup_buttons_layout.addWidget(self.dup_remove_folder_button)
        duplicate_finder_layout.addLayout(dup_buttons_layout)

        self.dup_scan_button = QPushButton("Scan for Duplicates")
        self.dup_scan_button.clicked.connect(self.handle_scan_button_clicked)
        self.dup_scan_button.setEnabled(False)
        duplicate_finder_layout.addWidget(self.dup_scan_button)

        self.dup_cancel_scan_button = QPushButton("Cancel Scan")
        self.dup_cancel_scan_button.clicked.connect(self.cancel_duplicate_scan)
        self.dup_cancel_scan_button.setEnabled(False)
        duplicate_finder_layout.addWidget(self.dup_cancel_scan_button)


        dup_results_label = QLabel("Duplicate Sets:")
        duplicate_finder_layout.addWidget(dup_results_label)

        self.dup_results_tree = QTreeWidget()
        self.dup_results_tree.setHeaderLabels(["File Name", "Size (MB)", "Date Modified", "Path"])
        self.dup_results_tree.itemSelectionChanged.connect(self.update_dup_delete_button_state)
        duplicate_finder_layout.addWidget(self.dup_results_tree)

        self.dup_delete_button = QPushButton("Delete Selected Files")
        self.dup_delete_button.clicked.connect(self.handle_delete_button_clicked)
        self.dup_delete_button.setEnabled(False)
        duplicate_finder_layout.addWidget(self.dup_delete_button)

        self.dup_status_label = QLabel("Status: Ready. Add folders to scan.")
        duplicate_finder_layout.addWidget(self.dup_status_label)

        self.tab_widget.addTab(duplicate_finder_widget, "Duplicate Finder")
        self.type_scanner_thread = None # Initialize thread attribute

        # --- File Type Scanner Tab ---
        self.type_scanner_tab = QWidget()
        type_scanner_layout = QVBoxLayout(self.type_scanner_tab)

        # Directory Selection Area for Type Scanner
        type_dir_label = QLabel("Folders to Scan:")
        type_scanner_layout.addWidget(type_dir_label)

        self.type_scan_paths_list = QListWidget()
        self.type_scan_paths_list.model().rowsInserted.connect(self.update_type_scan_button_state)
        self.type_scan_paths_list.model().rowsRemoved.connect(self.update_type_scan_button_state)
        type_scanner_layout.addWidget(self.type_scan_paths_list)

        type_buttons_layout = QHBoxLayout()
        self.type_add_folder_button = QPushButton("Add Folder")
        self.type_add_folder_button.clicked.connect(self.add_type_scan_folder)
        type_buttons_layout.addWidget(self.type_add_folder_button)

        self.type_remove_folder_button = QPushButton("Remove Folder")
        self.type_remove_folder_button.clicked.connect(self.remove_type_scan_folder)
        type_buttons_layout.addWidget(self.type_remove_folder_button)
        type_scanner_layout.addLayout(type_buttons_layout)

        type_scan_actions_layout = QHBoxLayout() # Layout for Scan and Cancel buttons
        self.type_scan_button = QPushButton("Scan File Types")
        self.type_scan_button.clicked.connect(self.handle_type_scan_button_clicked)
        self.type_scan_button.setEnabled(False)
        type_scan_actions_layout.addWidget(self.type_scan_button)

        self.type_cancel_scan_button = QPushButton("Cancel Scan")
        self.type_cancel_scan_button.clicked.connect(self.cancel_type_scan)
        self.type_cancel_scan_button.setEnabled(False)
        type_scan_actions_layout.addWidget(self.type_cancel_scan_button)
        type_scanner_layout.addLayout(type_scan_actions_layout)


        # Results Area for Type Scanner
        type_results_label = QLabel("Scanned File Types:")
        type_scanner_layout.addWidget(type_results_label)

        self.type_results_tree = QTreeWidget()
        self.type_results_tree.setHeaderLabels(["File Name", "Path", "Identified Type", "Extension"])
        type_scanner_layout.addWidget(self.type_results_tree)

        self.type_status_label = QLabel("Status: Ready.")
        type_scanner_layout.addWidget(self.type_status_label)

        self.tab_widget.addTab(self.type_scanner_tab, "Type Scanner")


    # --- Methods for Duplicate Finder Tab state ---
    def update_dup_scan_button_state(self):
        self.dup_scan_button.setEnabled(self.dup_scan_paths_list.count() > 0)

    def update_dup_delete_button_state(self):
        # Enable if any checkable item is selected, or any item is checked
        # For simplicity, enable if any item is selected in the results tree for now
        # More robust: check if any actual file item is selected/checked
        is_item_selected = len(self.dup_results_tree.selectedItems()) > 0

        has_checked_item = False
        iterator = QTreeWidgetItemIterator(self.dup_results_tree)
        while iterator.value():
            item = iterator.value()
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable and item.checkState(0) == Qt.CheckState.Checked:
                has_checked_item = True
                break
            iterator += 1
        self.dup_delete_button.setEnabled(has_checked_item)


    # --- Methods for File Browser (existing) ---
    def set_sort_criteria(self, criteria):
        if self.sort_criteria == criteria:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_criteria = criteria
            self.sort_reverse = False
        self.load_directory_contents(self.current_path)

    def load_directory_contents(self, path):
        try:
            path = os.path.abspath(path)
            self.list_widget.clear()
            if not os.path.isdir(path):
                self.list_widget.addItem(f"Error: Not a directory - {path}")
                self.current_path = path
                self.address_bar.setText(self.current_path)
                return
            self.current_path = path
            self.address_bar.setText(self.current_path)
            items_details = []
            raw_items = os.listdir(path)
            for name in raw_items:
                item_path = os.path.join(path, name)
                try:
                    is_dir = os.path.isdir(item_path)
                    size = os.path.getsize(item_path)
                    last_modified = os.path.getmtime(item_path)
                    _, ext = os.path.splitext(name)
                    item_type = ext.lower() if ext else ( "folder" if is_dir else "file")
                    items_details.append({
                        "name": name, "full_path": item_path, "is_dir": is_dir,
                        "size": size, "last_modified": last_modified, "type": item_type
                    })
                except OSError:
                    print(f"Could not retrieve details for {item_path}")
                    continue
            if self.sort_criteria == "name": items_details.sort(key=lambda x: x["name"].lower(), reverse=self.sort_reverse)
            elif self.sort_criteria == "date": items_details.sort(key=lambda x: x["last_modified"], reverse=self.sort_reverse)
            elif self.sort_criteria == "type": items_details.sort(key=lambda x: (x["type"], x["name"].lower()), reverse=self.sort_reverse)
            items_details.sort(key=lambda x: x["is_dir"], reverse=True)
            for item_detail in items_details:
                display_name = item_detail["name"]
                if item_detail["is_dir"]: display_name += "/"
                self.list_widget.addItem(display_name)
        except FileNotFoundError: self.list_widget.addItem(f"Error: Directory not found - {path}")
        except PermissionError: self.list_widget.addItem(f"Error: Permission denied - {path}")
        except Exception as e: self.list_widget.addItem(f"Error: {e}")

    def change_directory_from_address_bar(self):
        self.load_directory_contents(self.address_bar.text())

    def go_up_directory(self):
        parent_path = os.path.dirname(self.current_path)
        if parent_path != self.current_path: self.load_directory_contents(parent_path)

    def handle_item_double_click(self, item):
        item_name = item.text()
        if item_name.endswith("/"): item_name = item_name[:-1]
        potential_path = os.path.join(self.current_path, item_name)
        if os.path.isdir(potential_path): self.load_directory_contents(potential_path)

    # --- Methods for Duplicate Finder ---
    def add_scan_folder(self): # This is for Duplicate Finder
        directory = QFileDialog.getExistingDirectory(self, "Select Folder for Duplicate Scan")
        if directory:
            items = [self.dup_scan_paths_list.item(i).text() for i in range(self.dup_scan_paths_list.count())]
            if directory not in items:
                self.dup_scan_paths_list.addItem(directory)
                self.dup_status_label.setText(f"Added for duplicate scan: {directory}")
            else:
                self.dup_status_label.setText(f"Already added for duplicate scan: {directory}")

    def remove_scan_folder(self): # This is for Duplicate Finder
        current_item = self.dup_scan_paths_list.currentItem()
        if current_item:
            removed_text = current_item.text()
            self.dup_scan_paths_list.takeItem(self.dup_scan_paths_list.row(current_item))
            self.dup_status_label.setText(f"Removed from duplicate scan: {removed_text}")

    def handle_scan_button_clicked(self): # This is for Duplicate Finder
        paths = [self.dup_scan_paths_list.item(i).text() for i in range(self.dup_scan_paths_list.count())]
        if not paths:
            QMessageBox.warning(self, "No Folders", "Please add folders to scan.")
            return
        if self.dup_scanner_thread and self.dup_scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A scan is already running.")
            return

        self.dup_scan_button.setEnabled(False)
        self.dup_add_folder_button.setEnabled(False)
        self.dup_remove_folder_button.setEnabled(False)
        self.dup_cancel_scan_button.setEnabled(True)
        self.dup_results_tree.clear()
        self.dup_status_label.setText("Starting scan...")

        self.dup_scanner_thread = DuplicateScannerThread(paths)
        self.dup_scanner_thread.progress_updated.connect(self.update_scan_progress)
        self.dup_scanner_thread.scan_complete.connect(self.populate_scan_results)
        self.dup_scanner_thread.error_occurred.connect(self.handle_scan_error)
        self.dup_scanner_thread.finished.connect(self.scan_thread_finished)
        self.dup_scanner_thread.start()

    def cancel_duplicate_scan(self):
        if self.dup_scanner_thread and self.dup_scanner_thread.isRunning():
            self.dup_scanner_thread.stop() # Tell the thread to stop
            self.dup_status_label.setText("Status: Cancelling scan...")
            # UI will be fully re-enabled in scan_thread_finished

    def update_scan_progress(self, message, percentage):
        self.dup_status_label.setText(f"{message} [{percentage}%]")

    def populate_scan_results(self, duplicate_sets):
        self.dup_results_tree.clear()
        if not duplicate_sets:
            self.dup_status_label.setText("Scan complete. No duplicates found.")
            return
        self.dup_status_label.setText(f"Scan complete. Found {len(duplicate_sets)} sets of duplicates.")
        for i, group in enumerate(duplicate_sets):
            group_item_text = f"Duplicate Set {i+1} ({len(group)} files)"
            group_item = QTreeWidgetItem(self.dup_results_tree, [group_item_text, "", "", ""])
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsUserCheckable)
            for filepath in group:
                try:
                    size_bytes = os.path.getsize(filepath)
                    size_mb = "{:.2f}".format(size_bytes / (1024 * 1024))
                    modified_timestamp = os.path.getmtime(filepath)
                    modified_date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified_timestamp))
                    file_item = QTreeWidgetItem(group_item, [os.path.basename(filepath), size_mb, modified_date_str, filepath])
                    file_item.setData(3, Qt.ItemDataRole.UserRole, filepath) # Store full path in the path column's UserRole
                    file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    file_item.setCheckState(0, Qt.CheckState.Unchecked) # Checkbox in the first column
                except OSError as e:
                    error_item = QTreeWidgetItem(group_item, [os.path.basename(filepath), "Error", str(e), filepath])
                    error_item.setDisabled(True)
        self.dup_results_tree.expandAll()
        # self.dup_delete_button.setEnabled(True) # Enable delete button - will be handled by itemSelectionChanged/checked logic
        self.update_dup_delete_button_state()


    def handle_scan_error(self, error_message):
        self.dup_status_label.setText(f"Error: {error_message}")
        QMessageBox.critical(self, "Scan Error", error_message)
        # scan_thread_finished will be called anyway, re-enabling UI

    def scan_thread_finished(self):
        self.dup_scan_button.setEnabled(self.dup_scan_paths_list.count() > 0)
        self.dup_add_folder_button.setEnabled(True)
        self.dup_remove_folder_button.setEnabled(True)
        self.dup_cancel_scan_button.setEnabled(False)
        if self.dup_status_label.text().startswith("Status: Cancelling scan..."): # If cancelled
             self.dup_status_label.setText("Status: Scan cancelled.")
        elif not self.dup_scanner_thread or not self.dup_scanner_thread.error_occurred.connect: # Check if thread emitted error
             if self.dup_results_tree.topLevelItemCount() == 0 and not "No duplicates found" in self.dup_status_label.text():
                 self.dup_status_label.setText("Status: Scan finished or stopped early.")


        self.dup_scanner_thread = None
        self.update_dup_delete_button_state()

    def handle_delete_button_clicked(self):
        files_to_delete = []
        iterator = QTreeWidgetItemIterator(self.dup_results_tree)
        while iterator.value():
            item = iterator.value()
            # Check if it's a file item (has a full path in UserRole data for the path column)
            # and if its checkbox in the first column is checked.
            if item.data(3, Qt.ItemDataRole.UserRole) and item.checkState(0) == Qt.CheckState.Checked:
                files_to_delete.append(item.data(3, Qt.ItemDataRole.UserRole))
            iterator += 1

        if not files_to_delete:
            QMessageBox.information(self, "No Files Selected", "Please select files to delete by checking them.")
            return

        reply = QMessageBox.warning(self, "Confirm Deletion",
                                    f"Are you sure you want to delete {len(files_to_delete)} files? This action cannot be undone.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            error_count = 0
            errors = []
            for filepath in files_to_delete:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except OSError as e:
                    error_count += 1
                    errors.append(f"Could not delete {filepath}: {e}")

            summary_message = f"{deleted_count} files deleted."
            if error_count > 0:
                summary_message += f"\n{error_count} errors occurred. Details:\n" + "\n".join(errors)
            QMessageBox.information(self, "Deletion Complete", summary_message)

            # Refresh the list - a simple way is to re-scan the same paths
            # Or, more efficiently, remove deleted items from tree and re-evaluate duplicates
            self.dup_results_tree.clear() # Clear tree
            self.dup_status_label.setText("Deletion complete. Please scan again to refresh results.")
            self.dup_delete_button.setEnabled(False)
            # Consider re-enabling scan button if paths are still present
            self.dup_scan_button.setEnabled(self.dup_scan_paths_list.count() > 0)

    # --- Methods for File Type Scanner Tab ---
    def add_type_scan_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Folder for Type Scan")
        if directory:
            items = [self.type_scan_paths_list.item(i).text() for i in range(self.type_scan_paths_list.count())]
            if directory not in items:
                self.type_scan_paths_list.addItem(directory)
                self.type_status_label.setText(f"Added for type scan: {directory}")
            else:
                self.type_status_label.setText(f"Already added for type scan: {directory}")

    def remove_type_scan_folder(self):
        current_item = self.type_scan_paths_list.currentItem()
        if current_item:
            removed_text = current_item.text()
            self.type_scan_paths_list.takeItem(self.type_scan_paths_list.row(current_item))
            self.type_status_label.setText(f"Removed from type scan: {removed_text}")

    def update_type_scan_button_state(self):
        self.type_scan_button.setEnabled(self.type_scan_paths_list.count() > 0)

    def handle_type_scan_button_clicked(self):
        paths = [self.type_scan_paths_list.item(i).text() for i in range(self.type_scan_paths_list.count())]
        if not paths:
            QMessageBox.warning(self, "No Folders", "Please add folders to scan for file types.")
            return

        if self.type_scanner_thread and self.type_scanner_thread.isRunning():
            QMessageBox.information(self, "Scan in Progress", "A file type scan is already running.")
            return

        self.type_add_folder_button.setEnabled(False)
        self.type_remove_folder_button.setEnabled(False)
        self.type_scan_button.setEnabled(False)
        self.type_cancel_scan_button.setEnabled(True)

        self.type_results_tree.clear()
        self.type_status_label.setText("Starting file type scan...")

        self.type_scanner_thread = FileTypeScannerThread(paths)
        self.type_scanner_thread.progress_updated.connect(self.update_type_scan_progress)
        self.type_scanner_thread.scan_complete.connect(self.populate_type_scan_results)
        self.type_scanner_thread.error_occurred.connect(self.handle_type_scan_error)
        self.type_scanner_thread.finished.connect(self.type_scan_thread_finished)
        self.type_scanner_thread.start()

    def cancel_type_scan(self):
        if self.type_scanner_thread and self.type_scanner_thread.isRunning():
            self.type_scanner_thread.stop()
            self.type_status_label.setText("Cancelling file type scan...")
            # self.type_cancel_scan_button.setEnabled(False) # Re-enabled/disabled in finished slot

    def update_type_scan_progress(self, message, percentage):
        self.type_status_label.setText(f"{message} [{percentage}%]" if percentage > 0 or message == "File type scan process complete." else message)

    def populate_type_scan_results(self, scanned_files_data):
        self.type_results_tree.clear()
        if not scanned_files_data:
            self.type_status_label.setText("Scan complete. No files found or scanned.")
            return

        self.type_status_label.setText(f"Scan complete. Processed {len(scanned_files_data)} files.")
        for file_data in scanned_files_data:
            item = QTreeWidgetItem(self.type_results_tree)
            item.setText(0, file_data["filename"])
            item.setText(1, file_data["filepath"])
            item.setText(2, file_data["identified_type"])
            item.setText(3, file_data["extension"])

        for i in range(self.type_results_tree.columnCount()):
            self.type_results_tree.resizeColumnToContents(i)

    def handle_type_scan_error(self, error_message):
        self.type_status_label.setText(f"Type Scan Error: {error_message}")
        QMessageBox.critical(self, "File Type Scan Error", error_message)
        # UI re-enabling is handled by type_scan_thread_finished

    def type_scan_thread_finished(self):
        self.type_add_folder_button.setEnabled(True)
        self.type_remove_folder_button.setEnabled(True)
        self.update_type_scan_button_state() # Sets scan button based on paths list
        self.type_cancel_scan_button.setEnabled(False)

        current_status = self.type_status_label.text()
        if self.type_scanner_thread and not self.type_scanner_thread.isRunning():
            if "Cancelling" in current_status:
                 self.type_status_label.setText("File type scan cancelled.")
            # elif "Error" not in current_status: # Don't overwrite error messages
            #     self.type_status_label.setText("File type scan finished.")
            # If no error and not cancelled, populate_type_scan_results should have set the final status.

        self.type_scanner_thread = None
