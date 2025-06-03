import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QListWidget, QHBoxLayout,
                             QLineEdit, QPushButton)
# QMenu, QToolButton will be considered if simple PushButtons are not enough

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Manager")
        self.current_path = os.path.expanduser("~")
        self.sort_criteria = "name"  # Default sort: name
        self.sort_reverse = False    # Default sort: ascending

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        # Navigation bar
        nav_layout = QHBoxLayout()
        self.address_bar = QLineEdit()
        self.address_bar.setText(self.current_path)
        self.address_bar.returnPressed.connect(self.change_directory_from_address_bar)
        nav_layout.addWidget(self.address_bar)

        up_button = QPushButton("Up")
        up_button.clicked.connect(self.go_up_directory)
        nav_layout.addWidget(up_button)
        self.main_layout.addLayout(nav_layout)

        # Sorting controls
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
        self.main_layout.addLayout(sort_layout)

        # File and directory list
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.handle_item_double_click)
        self.main_layout.addWidget(self.list_widget)

        self.load_directory_contents(self.current_path)

    def set_sort_criteria(self, criteria):
        if self.sort_criteria == criteria:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_criteria = criteria
            self.sort_reverse = False # Default to ascending when criteria changes
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
                        "name": name,
                        "full_path": item_path,
                        "is_dir": is_dir,
                        "size": size,
                        "last_modified": last_modified,
                        "type": item_type
                    })
                except OSError: # Catch errors like permission denied for individual files
                    # Optionally log this or add a placeholder item
                    print(f"Could not retrieve details for {item_path}")
                    continue


            # Sorting logic
            if self.sort_criteria == "name":
                items_details.sort(key=lambda x: x["name"].lower(), reverse=self.sort_reverse)
            elif self.sort_criteria == "date":
                items_details.sort(key=lambda x: x["last_modified"], reverse=self.sort_reverse)
            elif self.sort_criteria == "type":
                # Sort by type, then by name for tie-breaking
                items_details.sort(key=lambda x: (x["type"], x["name"].lower()), reverse=self.sort_reverse)

            # Group directories first, then files, within each sort criteria
            # This is a common UX pattern.
            items_details.sort(key=lambda x: x["is_dir"], reverse=True)


            for item_detail in items_details:
                display_name = item_detail["name"]
                if item_detail["is_dir"]:
                    display_name += "/"
                self.list_widget.addItem(display_name)

        except FileNotFoundError:
            self.list_widget.addItem(f"Error: Directory not found - {path}")
            # self.current_path should ideally not be updated to a non-existent path
        except PermissionError:
            self.list_widget.addItem(f"Error: Permission denied - {path}")
            # self.current_path might need careful handling here too
        except Exception as e:
            self.list_widget.addItem(f"Error: {e}")
            # self.current_path might need careful handling here too

    def change_directory_from_address_bar(self):
        new_path = self.address_bar.text()
        self.load_directory_contents(new_path)

    def go_up_directory(self):
        parent_path = os.path.dirname(self.current_path)
        if parent_path != self.current_path: # Avoid getting stuck at root
            self.load_directory_contents(parent_path)

    def handle_item_double_click(self, item):
        item_name = item.text()
        # Remove trailing slash if it's a directory
        if item_name.endswith("/"):
            item_name = item_name[:-1]

        potential_path = os.path.join(self.current_path, item_name)

        if os.path.isdir(potential_path):
            self.load_directory_contents(potential_path)
        # else:
            # Optionally handle file double-click (e.g., open file)
            # For now, only directories are interactive on double-click
