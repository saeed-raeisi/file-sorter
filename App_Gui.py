import sys
import os
import time # For formatting date
import shutil # Added for delete action
import os
import time # For formatting date
import shutil # Added for delete action
import datetime # Added for Properties
import stat     # Added for Properties
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QListWidget, QHBoxLayout,
                             QLineEdit, QPushButton, QTabWidget, QFileDialog,
                             QTreeWidget, QTreeWidgetItem, QLabel, QMessageBox,
                             QTreeWidgetItemIterator, QMenu, QAbstractItemView,
                             QInputDialog, QDialog, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt
from duplicate_finder_logic import DuplicateScannerThread
from file_type_scanner_logic import FileTypeScannerThread
from file_search_logic import FileSearchThread # Added FileSearchThread
from file_search_logic import FileSearchThread # Added FileSearchThread

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

        # Search UI
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search in current folder and subfolders (Enter to search)...")
        self.search_bar.returnPressed.connect(self.handle_file_search) # Connect here
        search_layout.addWidget(self.search_bar)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.handle_file_search) # Connect here
        search_layout.addWidget(self.search_button)

        self.clear_search_button = QPushButton("Clear Search / Back")
        self.clear_search_button.clicked.connect(self.clear_file_search_view) # Connect here
        search_layout.addWidget(self.clear_search_button)
        self.file_browser_layout.addLayout(search_layout)

        self.search_thread = None
        self.is_search_view_active = False

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.handle_item_double_click)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_file_browser_context_menu)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) # Enable multi-selection
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
        # Guard against reloading if search view is active and path hasn't changed by explicit navigation
        # and not currently in the process of clearing search for a new load.
        if self.is_search_view_active and path == self.current_path and not hasattr(self, '_clearing_search'):
            # print("load_directory_contents: Search view active on same path, refresh via 'Clear Search'.")
            return

        # If navigating to a new path (e.g. via address bar, double-click, up button), clear search.
        # Check _clearing_search to prevent recursion if called from clear_file_search_view itself.
        if self.is_search_view_active and path != self.current_path and not hasattr(self, '_clearing_search'):
            self.clear_file_search_view(new_path_to_load_after_clear=path)
            return # clear_file_search_view will call load_directory_contents again

        try:
            path = os.path.abspath(path)
            self.list_widget.clear()

            if not os.path.isdir(path):
                self.list_widget.addItem(f"Error: Not a directory - {path}")
                self.current_path = path
                self.address_bar.setText(self.current_path)
                return

            # Path is valid and is a directory
            self.current_path = path
            # Only update address bar text if not in search view or if search is being cleared.
            if not self.is_search_view_active or hasattr(self, '_clearing_search'):
                 self.address_bar.setText(self.current_path)
            # If it was a direct navigation, ensure search view is false.
            # If called from clear_file_search_view, is_search_view_active is already false.
            # self.is_search_view_active = False # This is now handled more carefully in clear_file_search_view
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
        if self.is_search_view_active:
            full_path = item.data(Qt.ItemDataRole.UserRole)
            if full_path:
                if os.path.isdir(full_path):
                    self.clear_file_search_view(new_path_to_load_after_clear=full_path)
                elif os.path.isfile(full_path):
                    try:
                        if sys.platform == "win32": os.startfile(full_path)
                        elif sys.platform == "darwin": os.system(f'open "{full_path}"')
                        else: os.system(f'xdg-open "{full_path}"')
                    except Exception as e:
                        QMessageBox.warning(self, "Open File Error", f"Could not open file '{os.path.basename(full_path)}':\n{e}")
            return

        # Original double-click logic for file browser view
        item_name_display = item.text()
        item_name_for_path = item_name_display.rstrip('/')
        potential_path = os.path.join(self.current_path, item_name_for_path)

        if os.path.isdir(potential_path):
            self.load_directory_contents(potential_path)
        elif os.path.isfile(potential_path):
             try:
                if sys.platform == "win32": os.startfile(potential_path)
                elif sys.platform == "darwin": os.system(f'open "{potential_path}"')
                else: os.system(f'xdg-open "{potential_path}"')
             except Exception as e:
                QMessageBox.warning(self, "Open File Error", f"Could not open file '{os.path.basename(potential_path)}':\n{e}")

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

    # --- File Search Methods ---
    def handle_file_search(self):
        search_term = self.search_bar.text().strip()
        if not search_term:
            if self.is_search_view_active:
                self.clear_file_search_view()
            else:
                QMessageBox.information(self, "Search", "Please enter a search term.")
            return

        if self.search_thread and self.search_thread.isRunning():
            QMessageBox.information(self, "Search", "A search is already in progress. Please cancel or wait.")
            return

        self.list_widget.clear()
        self.is_search_view_active = True

        self.type_status_label.setText(f"Searching for '{search_term}' in '{self.current_path}'...")
        self.address_bar.setText(f"Search Results: '{search_term}' (in '{os.path.basename(self.current_path)}')")

        self.search_button.setEnabled(False)
        self.clear_search_button.setText("Cancel Search")

        self.search_thread = FileSearchThread(self.current_path, search_term)
        self.search_thread.search_progress.connect(self.update_search_progress)
        self.search_thread.search_complete.connect(self.display_search_results)
        self.search_thread.search_error.connect(self.handle_search_error)
        self.search_thread.finished.connect(self.search_thread_finished)
        self.search_thread.start()

    def update_search_progress(self, message):
        self.type_status_label.setText(f"Search: {message}")

    def display_search_results(self, matches):
        self.list_widget.clear()
        if not self.is_search_view_active:
            return

        if not matches:
            self.list_widget.addItem("No results found.")
            self.type_status_label.setText(f"Search complete. No results for '{self.search_bar.text()}'.")
            return

        self.type_status_label.setText(f"Search complete. Found {len(matches)} items.")

        for path_match in matches:
            display_name = os.path.basename(path_match)
            list_item_text = display_name

            item = QListWidgetItem(list_item_text)
            item.setData(Qt.ItemDataRole.UserRole, path_match)
            item.setToolTip(path_match)

            try:
                if os.path.isdir(path_match):
                    item.setText(f"[D] {display_name}") # Prepend [D] for visual cue
                # else: item.setText(display_name) # No specific cue for files in search result
            except OSError:
                 item.setText(display_name + " (Error accessing)")
            self.list_widget.addItem(item)

        # print("Search results displayed.") # Console confirmation

    def handle_search_error(self, error_message):
        if not self.is_search_view_active: return
        QMessageBox.critical(self, "Search Error", error_message)
        self.type_status_label.setText(f"Search error: {error_message}")
        # search_thread_finished will be called, which resets some UI state.

    def search_thread_finished(self):
        self.search_button.setEnabled(True)
        self.clear_search_button.setText("Clear Search / Back")

        final_status = self.type_status_label.text()
        if self.search_thread and not self.search_thread._is_running :
            final_status = "Search cancelled."
        # Avoid overwriting specific error or "no results" messages
        elif "Search complete" not in final_status and "Search error" not in final_status and "Search cancelled" not in final_status:
             final_status = "Search finished."

        self.type_status_label.setText(final_status)
        self.search_thread = None

    def clear_file_search_view(self, new_path_to_load_after_clear=None):
        # Flag to prevent re-entry issues with load_directory_contents
        if hasattr(self, '_clearing_search') and self._clearing_search:
            return
        self._clearing_search = True

        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop()
            # Don't wait here; let 'finished' signal handle final UI updates for responsiveness.

        self.search_bar.clear()
        self.is_search_view_active = False # Critical: set before calling load_directory_contents

        self.search_button.setEnabled(True)
        self.clear_search_button.setText("Clear Search / Back")

        path_to_load = new_path_to_load_after_clear if new_path_to_load_after_clear is not None else self.current_path

        self.load_directory_contents(path_to_load)
        self.type_status_label.setText("Status: Ready.")

        if hasattr(self, '_clearing_search'):
            delattr(self, '_clearing_search')


    # --- Context Menu for File Browser ---
    def show_file_browser_context_menu(self, position):
        menu = QMenu()
        selected_list_widget_items = self.list_widget.selectedItems()
        item_at_pos = self.list_widget.itemAt(position)

        action_delete = menu.addAction("Delete")
        action_rename = menu.addAction("Rename")
        action_properties = menu.addAction("Properties")
        action_create_folder = menu.addAction("Create New Folder")
        menu.addSeparator()
        action_refresh = menu.addAction("Refresh")

        if self.is_search_view_active:
            action_refresh.triggered.connect(self.clear_file_search_view) # Refresh in search clears search
            # Create folder in search view operates on original current_path after confirmation
            action_create_folder.triggered.connect(self.create_new_folder_in_current_dir)
        else: # Normal browser view
            action_refresh.triggered.connect(lambda: self.load_directory_contents(self.current_path))
            action_create_folder.triggered.connect(self.create_new_folder_in_current_dir)

        if item_at_pos:
            num_selected = len(selected_list_widget_items)

            action_delete.setEnabled(num_selected > 0)
            action_rename.setEnabled(num_selected == 1)
            action_properties.setEnabled(num_selected == 1)
            action_create_folder.setEnabled(False) # Create folder is for empty space

            if num_selected > 0: action_delete.triggered.connect(self.delete_selected_items)
            if num_selected == 1:
                action_rename.triggered.connect(self.rename_selected_item)
                action_properties.triggered.connect(self.show_item_properties)
        else: # Clicked on empty space
            action_delete.setEnabled(False)
            action_rename.setEnabled(False)
            action_properties.setEnabled(False)
            action_create_folder.setEnabled(True)
            # Connection for create_folder already handled by view mode check

        menu.exec(self.list_widget.mapToGlobal(position))

    def show_item_properties(self):
        selected_list_items = self.list_widget.selectedItems()
        if not selected_list_items or len(selected_list_items) > 1: return

        list_item = selected_list_items[0]
        item_name_for_error_msg = list_item.text()

        if self.is_search_view_active:
            full_path = list_item.data(Qt.ItemDataRole.UserRole)
            if not full_path :
                QMessageBox.information(self, "Properties", f"Could not determine item path for '{item_name_for_error_msg}' from search result.")
                return
        else:
            item_name_display = list_item.text()
            item_name_for_path = item_name_display.rstrip('/')
            full_path = os.path.join(self.current_path, item_name_for_path)

        if not os.path.exists(full_path) and not os.path.islink(full_path):
             QMessageBox.warning(self, "Properties Error", f"Item '{os.path.basename(full_path)}' no longer exists.")
             if not self.is_search_view_active: self.load_directory_contents(self.current_path)
             elif list_item:
                 row = self.list_widget.row(list_item)
                 if row != -1: self.list_widget.takeItem(row)
             return

        dialog = PropertiesDialog(full_path, self)
        dialog.exec()

    def create_new_folder_in_current_dir(self):
        target_path_for_new_folder = self.current_path

        if self.is_search_view_active:
            reply = QMessageBox.information(self, "Create Folder",
                                           f"This will create a new folder in the last browsed directory: '{target_path_for_new_folder}'.\nThe current search view will be cleared. Continue?",
                                           QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel:
                return
            self._clearing_search = True # Use the flag correctly
            self.clear_file_search_view(new_path_to_load_after_clear=target_path_for_new_folder)
            if hasattr(self, '_clearing_search'): delattr(self, '_clearing_search')
        folder_name, ok = QInputDialog.getText(self, "Create New Folder",
                                               "Enter folder name:")

        if ok and folder_name:
            # Basic validation for folder name (e.g., no slashes, etc.) could be added here
            # For now, rely on OS to reject invalid names
            new_folder_path = os.path.join(self.current_path, folder_name)

            if os.path.exists(new_folder_path):
                QMessageBox.warning(self, "Create Folder Error",
                                    f"A file or folder named '{folder_name}' already exists in this location.")
                return

            try:
                os.makedirs(new_folder_path)
                print(f"Created folder: {new_folder_path}") # Using print for now
                self.load_directory_contents(self.current_path) # Refresh list
            except OSError as e:
                print(f"Error creating folder '{folder_name}': {e}") # Using print for now
                QMessageBox.critical(self, "Create Folder Error",
                                     f"Error creating folder '{folder_name}':\n{e}")
        elif ok and not folder_name: # User pressed OK but entered an empty name
            QMessageBox.warning(self, "Create Folder Error", "Folder name cannot be empty.")

    def rename_selected_item(self):
        selected_list_items = self.list_widget.selectedItems()
        if not selected_list_items or len(selected_list_items) > 1: return

        list_item = selected_list_items[0]
        old_name_display_from_list = list_item.text()

        if self.is_search_view_active:
            old_full_path = list_item.data(Qt.ItemDataRole.UserRole)
            if not old_full_path:
                QMessageBox.information(self, "Rename", "Could not determine item's full path from search result.")
                return
            current_dir_of_item = os.path.dirname(old_full_path)
            old_name = os.path.basename(old_full_path)
        else: # Normal view
            old_name = old_name_display_from_list.rstrip('/')
            old_full_path = os.path.join(self.current_path, old_name)
            current_dir_of_item = self.current_path

        new_name, ok = QInputDialog.getText(self, "Rename Item",
                                            f"Enter new name for '{old_name}':",
                                            text=old_name)
        if ok and new_name:
            if new_name == old_name: return
            new_full_path = os.path.join(current_dir_of_item, new_name)

            if os.path.exists(new_full_path):
                QMessageBox.warning(self, "Rename Error", f"An item named '{new_name}' already exists in '{current_dir_of_item}'.")
                return
            try:
                os.rename(old_full_path, new_full_path)
                print(f"Renamed '{old_name_display_from_list}' to '{new_name}'")
                if self.is_search_view_active:
                    # Update item in search view
                    list_item.setText(new_name + ("/" if os.path.isdir(new_full_path) else "")) # Keep visual cue if dir
                    list_item.setData(Qt.ItemDataRole.UserRole, new_full_path)
                    list_item.setToolTip(new_full_path)
                else:
                    self.load_directory_contents(self.current_path)
            except OSError as e:
                print(f"Error renaming '{old_name_display_from_list}': {e}")
                QMessageBox.critical(self, "Rename Error", f"Error renaming '{old_name_display_from_list}':\n{e}")
        elif ok and not new_name:
             QMessageBox.warning(self, "Rename Error", "New name cannot be empty.")


    def delete_selected_items(self):
        selected_list_items = self.list_widget.selectedItems()
        if not selected_list_items: return

        confirm_message = ""
        if self.is_search_view_active:
            confirm_message = f"Are you sure you want to delete {len(selected_list_items)} item(s) from search results?\nThis will affect their original locations."
        elif len(selected_list_items) == 1:
            confirm_message = f"Are you sure you want to delete '{selected_list_items[0].text()}'?"
        else:
            confirm_message = f"Are you sure you want to delete {len(selected_list_items)} selected items?"

        reply = QMessageBox.warning(self, "Confirm Delete", confirm_message,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            errors_occurred = False
            items_to_remove_from_gui_list = []

            for list_item_gui in selected_list_items:
                item_text_display = list_item_gui.text()

                if self.is_search_view_active:
                    full_path = list_item_gui.data(Qt.ItemDataRole.UserRole)
                    if not full_path:
                        QMessageBox.critical(self, "Delete Error", f"Could not determine path for '{item_text_display}'.")
                        errors_occurred = True
                        continue
                else: # Normal view
                    item_name_for_path = item_text_display.rstrip('/')
                    full_path = os.path.join(self.current_path, item_name_for_path)

                try:
                    if not os.path.exists(full_path) and not os.path.islink(full_path):
                        print(f"Error: Item '{item_text_display}' not found at '{full_path}' before deletion.")
                        QMessageBox.critical(self, "Delete Error", f"Could not find '{item_text_display}'. It may have been already removed.")
                        errors_occurred = True
                        if self.is_search_view_active: items_to_remove_from_gui_list.append(list_item_gui)
                        continue

                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                        print(f"Deleted directory: {full_path}")
                    elif os.path.isfile(full_path) or os.path.islink(full_path): # os.remove handles files and links
                        os.remove(full_path)
                        print(f"Deleted file/link: {full_path}")
                    else:
                        print(f"Error: Item '{item_text_display}' at '{full_path}' is not a file or directory.")
                        QMessageBox.critical(self, "Delete Error", f"Item '{item_text_display}' is not a file or directory.")
                        errors_occurred = True
                        continue # Skip to next item

                    if self.is_search_view_active: items_to_remove_from_gui_list.append(list_item_gui)
                except OSError as e:
                    print(f"Error deleting '{item_text_display}': {e}")
                    QMessageBox.critical(self, "Delete Error", f"Error deleting '{item_text_display}':\n{e}")
                    errors_occurred = True

            if self.is_search_view_active:
                for item_to_remove in items_to_remove_from_gui_list:
                    row = self.list_widget.row(item_to_remove)
                    if row != -1: self.list_widget.takeItem(row)
                if self.list_widget.count() == 0: self.list_widget.addItem("No results remaining.")
                final_status_msg = "Deletion from search results complete."
                if errors_occurred: final_status_msg += " Some errors occurred."
                print(final_status_msg)
                self.type_status_label.setText(final_status_msg)
            else: # Normal view
                self.load_directory_contents(self.current_path) # Refresh
                final_status_msg = "Deletion complete."
                if errors_occurred: final_status_msg += " Some errors occurred."
                print(final_status_msg)
                self.type_status_label.setText(final_status_msg)
