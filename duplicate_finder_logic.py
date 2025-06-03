import os
import hashlib
import collections
from PyQt6.QtCore import QThread, pyqtSignal

# Helper function (can be module-level or static inside the class if preferred)
def _calculate_hash(filepath, block_size=65536, error_callback=None):
    hash_obj = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(block_size)
                if not chunk:
                    break
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except IOError as e:
        if error_callback:
            error_callback(f"IOError calculating hash for {filepath}: {e}")
        else:
            print(f"IOError calculating hash for {filepath}: {e}")
        return None
    except OSError as e:
        if error_callback:
            error_callback(f"OSError calculating hash for {filepath}: {e}")
        else:
            print(f"OSError calculating hash for {filepath}: {e}")
        return None

def find_duplicates_core(directories_to_scan, progress_callback=None, error_callback=None, is_running_check=None):
    files_by_size = collections.defaultdict(list)
    duplicates_found = []

    def _emit_progress(message, percentage):
        if progress_callback:
            progress_callback(message, percentage)

    def _emit_error(message):
        if error_callback:
            error_callback(message)
        else: # Fallback if no error callback provided during direct calls
            print(f"Error (core logic): {message}")


    _emit_progress("Phase 1: Scanning files and grouping by size...", 0)

    total_dirs = len(directories_to_scan)
    processed_dirs = 0
    files_scanned_phase1 = 0

    for directory in directories_to_scan:
        if is_running_check and not is_running_check(): return duplicates_found

        if not os.path.isdir(directory): # Check if directory exists and is a directory
            _emit_error(f"Directory not found or not a directory: {directory}")
            processed_dirs += 1 # Count it as processed for progress calculation
            continue # Skip to the next directory

        try:
            for dirpath, _, filenames in os.walk(directory):
                if is_running_check and not is_running_check(): return duplicates_found
                for filename in filenames:
                    if is_running_check and not is_running_check(): return duplicates_found
                    filepath = os.path.join(dirpath, filename)
                    try:
                        if os.path.islink(filepath):
                            continue
                        size = os.path.getsize(filepath)
                        files_by_size[size].append(filepath)
                        files_scanned_phase1 += 1
                        if files_scanned_phase1 % 100 == 0:
                            _emit_progress(f"Scanned {files_scanned_phase1} files...", (processed_dirs * 100) // total_dirs if total_dirs > 0 else 50)
                    except os.error as e:
                        _emit_error(f"Error accessing file (size) {filepath}: {e}")
        except Exception as e:
            _emit_error(f"Error walking directory {directory}: {e}")

        if is_running_check and not is_running_check(): return duplicates_found
        processed_dirs += 1
        _emit_progress(f"Completed scanning directory {directory} ({processed_dirs}/{total_dirs})", (processed_dirs * 100) // total_dirs if total_dirs > 0 else 100)

    if is_running_check and not is_running_check(): return duplicates_found
    _emit_progress("Phase 1 Complete. Starting Phase 2: Hashing potential duplicates...", 0)

    potential_duplicate_groups = {size: files for size, files in files_by_size.items() if len(files) > 1}
    total_files_to_hash = sum(len(files) for files in potential_duplicate_groups.values())
    hashed_files_count = 0

    for size, filepaths_list in potential_duplicate_groups.items():
        if is_running_check and not is_running_check(): return duplicates_found
        if len(filepaths_list) > 1:
            hashes_for_size_group = collections.defaultdict(list)
            for filepath in filepaths_list:
                if is_running_check and not is_running_check(): return duplicates_found

                current_progress_msg = f"Hashing (Size {size}): {os.path.basename(filepath)}"
                percentage = (hashed_files_count * 100) // total_files_to_hash if total_files_to_hash > 0 else 0
                _emit_progress(current_progress_msg, percentage)

                file_hash = _calculate_hash(filepath, error_callback=_emit_error) # Pass error_callback
                if file_hash:
                    hashes_for_size_group[file_hash].append(filepath)
                # else: # _calculate_hash now calls error_callback directly
                #     _emit_error(f"Failed to calculate hash for {filepath}. Skipping.")

                hashed_files_count += 1

            for hash_value, duplicate_paths in hashes_for_size_group.items():
                if len(duplicate_paths) > 1:
                    duplicates_found.append(list(duplicate_paths))

    if is_running_check and not is_running_check(): return duplicates_found # Final check
    _emit_progress("Scan processing complete.", 100)
    return duplicates_found


class DuplicateScannerThread(QThread):
    progress_updated = pyqtSignal(str, int)
    scan_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, directories_to_scan, parent=None):
        super().__init__(parent)
        self.directories_to_scan = directories_to_scan
        self._is_running = True

    def run(self):
        self._is_running = True # Ensure it's true at the start of run

        # Define wrappers for emitting signals
        def emit_progress(message, percentage):
            if not self._is_running: return # Avoid emitting if stopped during callback
            self.progress_updated.emit(message, percentage)

        def emit_error(message):
            if not self._is_running: return
            self.error_occurred.emit(message)

        def is_running_check():
            return self._is_running

        final_duplicates = []
        try:
            final_duplicates = find_duplicates_core(
                self.directories_to_scan,
                emit_progress,
                emit_error,
                is_running_check
            )
        except Exception as e:
            # Catch any unexpected errors from find_duplicates_core itself
            emit_error(f"Unexpected critical error in scan core: {e}")
        finally:
            # Only emit scan_complete if the thread wasn't stopped prematurely
            # or if it completed, regardless of whether duplicates were found.
            if self._is_running: # If not stopped by a call to self.stop()
                self.scan_complete.emit(final_duplicates)
            else:
                # If self.stop() was called, _is_running is False.
                # Emit scan_complete with potentially partial results, or empty list.
                # Or, you might choose not to emit if stopped, depends on desired behavior.
                # For now, let's emit what we have.
                self.scan_complete.emit(final_duplicates)
            self._is_running = False # Ensure state is updated post-run

    def stop(self):
        # This method is called from other threads.
        # It signals the run() method to stop.
        if self.progress_updated and self._is_running: # Check if signal exists (might be called during cleanup)
             try:
                self.progress_updated.emit("Scan stopping...", 0)
             except RuntimeError: # If event loop is gone
                 pass
        self._is_running = False
