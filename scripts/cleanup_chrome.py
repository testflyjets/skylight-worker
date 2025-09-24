#!/usr/bin/env python3
"""
Utility script to clean up orphaned Chrome processes.
This can be run manually or automatically to ensure no Chrome processes are left hanging.
"""

import psutil
import sys
import argparse
from typing import List

def find_chrome_processes() -> List[psutil.Process]:
    """Find all Chrome/Chromium processes on the system"""
    chrome_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = proc.info['name'].lower()
            if 'chrome' in name or 'chromium' in name:
                chrome_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return chrome_processes

def find_worker_chrome_processes() -> List[psutil.Process]:
    """Find Chrome processes that appear to be from selenium workers"""
    chrome_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
        try:
            name = proc.info['name'].lower()
            if 'chrome' in name or 'chromium' in name:
                # Check if the command line contains selenium-related arguments
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if any(keyword in cmdline.lower() for keyword in [
                    'user-data-dir', 'disable-blink-features', 'automation', 
                    'load-extension', 'pypasser', 'chromium_automation'
                ]):
                    chrome_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return chrome_processes

def cleanup_processes(processes: List[psutil.Process], force: bool = False) -> int:
    """Clean up the given Chrome processes"""
    if not processes:
        print("No Chrome processes found to clean up")
        return 0
    
    print(f"Found {len(processes)} Chrome processes to clean up:")
    for proc in processes:
        try:
            cmdline = ' '.join(proc.cmdline()[:3]) if proc.cmdline() else 'N/A'
            print(f"  PID {proc.pid}: {proc.name()} - {cmdline}...")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"  PID {proc.pid}: (process info unavailable)")
    
    if not force:
        response = input("\nDo you want to terminate these processes? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Cleanup cancelled")
            return 0
    
    # First, try graceful termination
    print("\nTerminating processes gracefully...")
    terminated = []
    for proc in processes:
        try:
            proc.terminate()
            terminated.append(proc)
            print(f"  Terminated PID {proc.pid}")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"  Could not terminate PID {proc.pid}: {e}")
    
    # Wait for graceful termination
    if terminated:
        print("Waiting for processes to exit...")
        gone, alive = psutil.wait_procs(terminated, timeout=5)
        
        # Force kill any that didn't terminate gracefully
        if alive:
            print("Force killing remaining processes...")
            for proc in alive:
                try:
                    proc.kill()
                    print(f"  Force killed PID {proc.pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"  Could not kill PID {proc.pid}: {e}")
    
    print(f"✅ Cleanup completed. Processed {len(processes)} Chrome processes.")
    return len(processes)

def main():
    parser = argparse.ArgumentParser(description='Clean up orphaned Chrome processes')
    parser.add_argument('--all', action='store_true', 
                       help='Clean up ALL Chrome processes (not just worker-related)')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt')
    parser.add_argument('--list-only', action='store_true',
                       help='Only list processes, do not clean up')
    
    args = parser.parse_args()
    
    print("Chrome Process Cleanup Utility")
    print("=" * 40)
    
    if args.all:
        print("Finding ALL Chrome processes...")
        processes = find_chrome_processes()
    else:
        print("Finding worker-related Chrome processes...")
        processes = find_worker_chrome_processes()
    
    if args.list_only:
        if not processes:
            print("No Chrome processes found")
        else:
            print(f"Found {len(processes)} Chrome processes:")
            for proc in processes:
                try:
                    cmdline = ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A'
                    print(f"  PID {proc.pid}: {proc.name()}")
                    print(f"    Command: {cmdline}")
                    print()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    print(f"  PID {proc.pid}: (process info unavailable)")
        return 0
    
    return cleanup_processes(processes, args.force)

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nCleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)
