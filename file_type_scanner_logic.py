import os
import magic # python-magic library
from PyQt6.QtCore import QThread, pyqtSignal

# Module-level core scanning function
def scan_files_core(directories_to_scan, progress_callback=None, error_callback=None, is_running_check=None):
    scanned_files_data = []

    try:
        # Create magic instance once: https://github.com/ahupp/python-magic#usage
        # Use unbuffered=True if files might be changing, but can be slower. Default is False.
        magic_instance = magic.Magic(mime=True)
    except magic.MagicException as e:
        if error_callback:
            error_callback(f"Failed to initialize libmagic: {e}. Ensure libmagic is installed correctly.")
        else:
            print(f"Failed to initialize libmagic: {e}. Ensure libmagic is installed correctly.")
        return scanned_files_data # Cannot proceed without magic_instance

    processed_files_count = 0
    dir_count = len(directories_to_scan)
    dirs_processed_count = 0

    for directory_path in directories_to_scan:
        if is_running_check and not is_running_check():
            break

        if not os.path.isdir(directory_path):
            if error_callback:
                error_callback(f"Directory not found or is not a directory: {directory_path}")
            dirs_processed_count +=1 # Still count as "processed" for progress
            continue

        # Update progress based on directories
        current_dir_progress = (dirs_processed_count * 100) // dir_count if dir_count > 0 else 0
        if progress_callback:
            progress_callback(f"Scanning: {os.path.basename(directory_path)}...", current_dir_progress)

        try:
            for root, _, files in os.walk(directory_path):
                if is_running_check and not is_running_check():
                    break
                for filename in files:
                    if is_running_check and not is_running_check():
                        break

                    filepath = os.path.join(root, filename)
                    extension = os.path.splitext(filename)[1].lower()
                    identified_type = "Unknown"

                    try:
                        if os.path.islink(filepath): # Skip symlinks
                            identified_type = "Symbolic Link"
                        else:
                            identified_type = magic_instance.from_file(filepath)
                    except magic.MagicException as e:
                        # This can happen for various reasons, e.g. empty files, permission issues for libmagic
                        identified_type = f"MagicError: {e}"
                        if error_callback: # Optionally report as an error too
                             error_callback(f"Libmagic error for {filepath}: {e}")
                    except Exception as e:
                        identified_type = "Unknown/Access Error"
                        if error_callback:
                            error_callback(f"Could not access/read file: {filepath} - {e}")

                    scanned_files_data.append({
                        "filename": filename,
                        "filepath": filepath,
                        "identified_type": identified_type,
                        "extension": extension
                    })

                    processed_files_count += 1
                    if progress_callback and processed_files_count % 50 == 0:
                        # File-based progress can be very granular; directory progress might be enough for UI
                        # For now, percentage is still based on directories, message indicates file count
                        progress_callback(f"Scanned {processed_files_count} files so far...", current_dir_progress)

                if is_running_check and not is_running_check(): # Check after processing all files in a dirpath
                    break
        except Exception as e: # Catch errors from os.walk itself (e.g. permissions on a directory it tries to enter)
            if error_callback:
                error_callback(f"Error during os.walk for {directory_path}: {e}")

        dirs_processed_count += 1
        if progress_callback: # Final progress update for this directory
             progress_callback(f"Finished scanning: {os.path.basename(directory_path)}", (dirs_processed_count * 100) // dir_count if dir_count > 0 else 100)


    if progress_callback:
        progress_callback("File type scan process complete.", 100)
    return scanned_files_data


class FileTypeScannerThread(QThread):
    progress_updated = pyqtSignal(str, int)
    scan_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, directories_to_scan, parent=None):
        super().__init__(parent)
        self.directories_to_scan = directories_to_scan
        self._is_running = True

    def run(self):
        self._is_running = True

        results = []
        try:
            # Define wrappers for emitting signals
            def progress_cb(message, percentage):
                if not self._is_running: return
                self.progress_updated.emit(message, percentage)

            def error_cb(message):
                if not self._is_running: return
                self.error_occurred.emit(message)

            def is_running_cb():
                return self._is_running

            results = scan_files_core(
                self.directories_to_scan,
                progress_cb,
                error_cb,
                is_running_cb
            )
        except Exception as e:
            # This is a fallback for truly unexpected errors in scan_files_core not caught by its own try-except
            if self._is_running: # Avoid emitting if stop() was called and caused an error during shutdown
                self.error_occurred.emit(f"Critical unexpected error in file type scanner: {e}")
        finally:
            if self._is_running:
                self.scan_complete.emit(results)
            # If stop() was called, _is_running is False.
            # We could emit partial results if desired: self.scan_complete.emit(results)
            # For now, only emitting if fully completed. User gets "stopping" message via progress.
            self._is_running = False

    def stop(self):
        if self._is_running: # Prevent multiple emits if stop is called more than once
            self._is_running = False
            try:
                # Emit "stopping" status only if the thread is actually running and has signals connected
                if self.progress_updated is not None: # Check if signal attribute exists
                     self.progress_updated.emit("File type scan stopping...", 0)
            except RuntimeError:
                # This can happen if the event loop is already torn down when stop() is called
                # (e.g. application shutting down)
                print("FileTypeScannerThread.stop(): Could not emit progress_updated, RuntimeError.")
                pass
            except Exception as e:
                print(f"FileTypeScannerThread.stop(): Error emitting progress: {e}")
