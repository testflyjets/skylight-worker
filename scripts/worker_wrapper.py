#!/usr/bin/env python3
"""
Worker wrapper script that handles setup before starting the actual worker.
This ensures all directories are created and environment is properly set up.
"""

import os
import sys
import subprocess
import signal
import psutil
from pathlib import Path

def setup_worker_environment():
    """Set up the worker environment before starting"""
    
    # Get environment variables
    worker_uid = os.environ.get('WORKER_UID', 'worker-01-KGAI')
    downloads_path = os.environ.get('DOWNLOADS_PATH', '/tmp/cache/worker_01')
    
    print(f"Setting up worker environment for {worker_uid}")
    print(f"Cache path: {downloads_path}")
    
    # Create all required directories
    directories = [
        downloads_path,
        f"{downloads_path}/.browser",
        f"{downloads_path}/.data",
        f"{downloads_path}/.disk",
        f"{downloads_path}/.globalcache"
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        except Exception as e:
            print(f"Failed to create directory {directory}: {e}")
            return False
    
    return True

def cleanup_chrome_processes():
    """Kill any orphaned Chrome processes"""
    try:
        current_pid = os.getpid()
        current_process = psutil.Process(current_pid)

        # Find all Chrome processes that are children of this process
        chrome_processes = []
        for child in current_process.children(recursive=True):
            try:
                if 'chrome' in child.name().lower() or 'chromium' in child.name().lower():
                    chrome_processes.append(child)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Terminate Chrome processes
        for chrome_proc in chrome_processes:
            try:
                print(f"Cleaning up Chrome process {chrome_proc.pid}")
                chrome_proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Wait for graceful termination
        if chrome_processes:
            psutil.wait_procs(chrome_processes, timeout=3)

        # Force kill any that didn't terminate
        for chrome_proc in chrome_processes:
            try:
                if chrome_proc.is_running():
                    print(f"Force killing Chrome process {chrome_proc.pid}")
                    chrome_proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    except Exception as e:
        print(f"Error during Chrome cleanup: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"Received signal {signum}, cleaning up...")
    cleanup_chrome_processes()
    sys.exit(0)

def start_worker():
    """Start the actual worker process"""

    # Set up signal handlers for cleanup
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Set up environment first
    if not setup_worker_environment():
        print("Failed to set up worker environment")
        sys.exit(1)

    # Get the project root directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    # Change to project directory
    os.chdir(project_dir)

    # Start the worker
    print("Starting selenium worker...")
    try:
        # Use exec to replace this process with the worker process
        # This ensures signals are handled properly
        os.execvp(sys.executable, [sys.executable, '-m', 'selenium_worker.app'])
    except Exception as e:
        print(f"Failed to start worker: {e}")
        cleanup_chrome_processes()
        sys.exit(1)

if __name__ == '__main__':
    start_worker()
