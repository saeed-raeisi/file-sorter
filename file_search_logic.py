import os
from PyQt6.QtCore import QThread, pyqtSignal

class FileSearchThread(QThread):
    search_progress = pyqtSignal(str)  # For status updates, e.g., "Searching in /path/to/dir..."
    search_complete = pyqtSignal(list) # Emits list of matching file/folder full paths
    search_error = pyqtSignal(str)     # For reporting errors

    def __init__(self, start_path, search_term, parent=None):
        super().__init__(parent)
        self.start_path = start_path
        self.search_term = search_term
        self._is_running = True

    def stop(self):
        self._is_running = False
        if self.search_progress: # Check if signal exists
            try:
                self.search_progress.emit("Search cancelling...") # Give immediate feedback
            except RuntimeError: # Event loop might be gone
                pass


    def run(self):
        self._is_running = True # Ensure it's true at the start of run
        matches = []

        if not self.search_term: # Should be caught by GUI, but as a safeguard
            self.search_error.emit("Search term cannot be empty.")
            return

        search_term_lower = self.search_term.lower()

        try:
            if not os.path.isdir(self.start_path):
                self.search_error.emit(f"Search path not found or not a directory: {self.start_path}")
                return

            for root, dirs, files in os.walk(self.start_path, topdown=True):
                if not self._is_running:
                    break

                try:
                    self.search_progress.emit(f"Searching in: {root}")
                except RuntimeError: # Gracefully handle if GUI/receiver is gone
                    self._is_running = False # Stop further processing
                    break


                # Filter directories in-place to avoid traversing unwanted paths if needed
                # For now, we search all directories.
                # Example: dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules']]

                for name in dirs: # Check directory names
                    if not self._is_running:
                        break
                    if search_term_lower in name.lower():
                        matches.append(os.path.join(root, name))
                if not self._is_running: break # Check after processing dirs in a root

                for name in files: # Check file names
                    if not self._is_running:
                        break
                    if search_term_lower in name.lower():
                        matches.append(os.path.join(root, name))
                if not self._is_running: break # Check after processing files in a root

        except Exception as e:
            if self._is_running: # Only emit error if not part of a graceful stop
                try:
                    self.search_error.emit(f"Error during search: {e}")
                except RuntimeError: # Gracefully handle if GUI/receiver is gone
                    pass
            return # Important to exit after an error

        finally: # Ensure signals are emitted correctly based on final state
            if not self._is_running: # Search was cancelled
                try:
                    self.search_progress.emit("Search cancelled.")
                    # Optionally emit empty list for complete if needed by GUI logic
                    # self.search_complete.emit([])
                except RuntimeError:
                    pass
            else: # Search completed normally (even if no matches or error occurred and was handled)
                try:
                    self.search_complete.emit(matches)
                except RuntimeError:
                    pass
            # Note: self._is_running = False is not set here, QThread handles finished state
            # The run method simply exits.
            # If stop() was called, _is_running is already False.
            # If run completes naturally, _is_running remains True until this exit.
            # The 'finished' signal from QThread will indicate completion.

            # Re-evaluating: _is_running should reflect the state for the thread's own logic.
            # When run() exits, the thread is considered finished by Qt.
            # The stop() method is the external way to signal termination.
            pass # Placeholder for any final cleanup if needed before thread truly ends.
