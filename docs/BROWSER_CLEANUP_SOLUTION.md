# Browser Cleanup Solution

## Problem Statement

When selenium workers are killed (especially by supervisor), Chrome browser instances were not being properly cleaned up, leading to:

- **Orphaned Chrome processes** consuming memory and CPU
- **Resource leaks** that accumulate over time
- **Port conflicts** when workers restart
- **System instability** with many orphaned processes

## Root Cause Analysis

The issue occurred because:

1. **Incomplete Shutdown**: The original `TaskService.shutdown()` only called `next(self._sb_gen)` which doesn't guarantee Chrome process termination
2. **Signal Handling**: When supervisor kills workers, the signal handler called `sys.exit(0)` without proper cleanup time
3. **Process Hierarchy**: Chrome spawns many helper processes that weren't being tracked and cleaned up
4. **Timing Issues**: Graceful shutdown wasn't given enough time before force termination

## Solution Implementation

### 1. Enhanced TaskService Shutdown

**File**: `selenium_worker/Services/TaskService.py`

```python
def shutdown(self, remove_user_data: bool = True):
    """Shutdown browser and cleanup resources"""
    import psutil
    
    # First, try to gracefully close the browser through SeleniumBase
    if self.SB:
        try:
            # Try to quit the driver first
            if self.driver:
                self.driver.quit()
            
            # Then close SeleniumBase
            next(self._sb_gen)
            self._sb_gen = None
            self.SB = None
        except Exception as e:
            self.log(f"Error during SeleniumBase shutdown: {e}")
    
    # Force kill any remaining Chrome processes
    try:
        current_pid = os.getpid()
        current_process = psutil.Process(current_pid)
        
        # Find all Chrome processes that are children of this worker
        chrome_processes = []
        for child in current_process.children(recursive=True):
            if 'chrome' in child.name().lower() or 'chromium' in child.name().lower():
                chrome_processes.append(child)
        
        # Terminate Chrome processes gracefully, then force kill if needed
        for chrome_proc in chrome_processes:
            chrome_proc.terminate()
        
        if chrome_processes:
            psutil.wait_procs(chrome_processes, timeout=5)
        
        # Force kill any that didn't terminate
        for chrome_proc in chrome_processes:
            if chrome_proc.is_running():
                chrome_proc.kill()
                
    except Exception as e:
        self.log(f"Error during Chrome process cleanup: {e}")
```

### 2. Improved Signal Handling

**File**: `selenium_worker/app.py`

```python
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global task_service
    global display
    
    logger.info(f'Received signal {signum}, shutting down gracefully...')
    
    try:
        # Cleanup browser and task service
        if task_service is not None:
            logger.info('Shutting down task service...')
            task_service.shutdown()
            
        # Cleanup display
        if display is not None:
            logger.info('Stopping virtual display...')
            display.stop()
            
    except Exception as e:
        logger.error(f'Error during signal handler cleanup: {e}')
    
    logger.info('Graceful shutdown complete')
    sys.exit(0)
```

### 3. Worker Wrapper with Cleanup

**File**: `scripts/worker_wrapper.py`

The wrapper script now includes:
- Signal handlers for cleanup
- Chrome process detection and termination
- Graceful shutdown with fallback to force kill

### 4. Supervisor Configuration Updates

**File**: `supervisor/supervisord.conf`

```ini
stopwaitsecs=45          # Give more time for graceful shutdown
stopsignal=TERM          # Use TERM signal for graceful shutdown
killasgroup=true         # Kill entire process group
stopasgroup=true         # Stop entire process group
```

### 5. Chrome Cleanup Utility

**File**: `scripts/cleanup_chrome.py`

A standalone utility that can:
- List all Chrome processes (worker-related or all)
- Clean up orphaned Chrome processes
- Force cleanup when needed
- Identify worker-related processes by command line arguments

## Usage

### Automatic Cleanup (Recommended)

Use the enhanced supervisor script:

```bash
# Start workers with automatic cleanup
./scripts/supervisor_macos_clean.sh start 4 KGAI

# Stop workers (includes Chrome cleanup)
./scripts/supervisor_macos_clean.sh stop
```

### Manual Cleanup

If you need to manually clean up orphaned Chrome processes:

```bash
# List worker-related Chrome processes
python3 scripts/cleanup_chrome.py --list-only

# Clean up worker-related Chrome processes
python3 scripts/cleanup_chrome.py

# Clean up ALL Chrome processes (use with caution)
python3 scripts/cleanup_chrome.py --all

# Force cleanup without confirmation
python3 scripts/cleanup_chrome.py --force
```

## Verification

To verify the solution is working:

1. **Start workers**:
   ```bash
   ./scripts/supervisor_macos_clean.sh start 2 KGAI
   ```

2. **Check Chrome processes are running**:
   ```bash
   python3 scripts/cleanup_chrome.py --list-only
   ```

3. **Stop workers**:
   ```bash
   ./scripts/supervisor_macos_clean.sh stop
   ```

4. **Verify Chrome processes are gone**:
   ```bash
   python3 scripts/cleanup_chrome.py --list-only
   # Should show: "No Chrome processes found"
   ```

## Technical Details

### Process Detection

The cleanup system identifies worker-related Chrome processes by looking for these command line arguments:
- `user-data-dir` (with worker cache paths)
- `disable-blink-features`
- `automation`
- `load-extension`
- `pypasser`
- `chromium_automation`

### Cleanup Strategy

1. **Graceful Termination**: Send SIGTERM to Chrome processes
2. **Wait Period**: Allow 5 seconds for graceful shutdown
3. **Force Kill**: Send SIGKILL to any remaining processes
4. **Verification**: Ensure all processes are terminated

### Dependencies

The solution requires:
- `psutil` Python package (added to requirements.txt)
- Proper signal handling in worker processes
- Enhanced supervisor configuration

## Benefits

✅ **No Orphaned Processes**: Chrome instances are properly cleaned up  
✅ **Resource Management**: Prevents memory and CPU leaks  
✅ **System Stability**: Avoids accumulation of zombie processes  
✅ **Automatic Operation**: Works transparently with supervisor  
✅ **Manual Override**: Cleanup utility for emergency situations  
✅ **Cross-Platform**: Works on macOS and Linux  

## Monitoring

The enhanced supervisor script provides feedback:
- Shows when Chrome cleanup is running
- Reports number of processes cleaned up
- Logs any cleanup errors

Log files to monitor:
- `/tmp/worker_*.log` - Individual worker logs
- `/tmp/supervisord.log` - Supervisor logs

## Troubleshooting

If Chrome processes are still orphaned:

1. **Check if cleanup ran**:
   ```bash
   grep -i chrome /tmp/supervisord.log
   ```

2. **Manual cleanup**:
   ```bash
   python3 scripts/cleanup_chrome.py --force
   ```

3. **Check for stuck processes**:
   ```bash
   ps aux | grep -i chrome
   ```

4. **System-wide cleanup** (last resort):
   ```bash
   sudo pkill -f chrome
   ```

The solution provides multiple layers of protection to ensure Chrome browser instances are properly managed throughout the worker lifecycle.
