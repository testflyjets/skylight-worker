# Supervisor Multi-Worker Deployment Guide

This guide covers the **recommended and only supported** method for running multiple selenium workers using supervisor.

## Overview

The supervisor solution provides:
- ✅ **Automatic process restart** on failure
- ✅ **Chrome browser cleanup** prevents orphaned processes  
- ✅ **Centralized logging** to `/tmp/worker_*.log`
- ✅ **Easy scaling** by changing worker count
- ✅ **macOS compatibility** with enhanced management script
- ✅ **Graceful shutdown** with proper cleanup

## Prerequisites

### 1. Install Supervisor

**macOS (Homebrew)**:
```bash
brew install supervisor
```

**Linux (pip)**:
```bash
pip install supervisor
```

**Verify Installation**:
```bash
supervisord --version
supervisorctl --version
```

### 2. Install Dependencies

Ensure `psutil` is installed for Chrome process cleanup:
```bash
pip install psutil
```

## Quick Start

### Start Workers
```bash
# Start 4 workers of type KGAI
./scripts/supervisor_macos_clean.sh start 4 KGAI
```

### Check Status
```bash
./scripts/supervisor_macos_clean.sh status
```

### Stop Workers
```bash
./scripts/supervisor_macos_clean.sh stop
```

## Configuration

### Supervisor Configuration

**File**: `supervisor/supervisord.conf`

Key settings:
- **Worker Count**: Set via `WORKER_COUNT` environment variable
- **Worker Type**: Set via `WORKER_TYPE` environment variable  
- **Unique UIDs**: Each worker gets `worker-00-KGAI`, `worker-01-KGAI`, etc.
- **Isolated Cache**: Each worker gets `/tmp/cache/worker_00/`, `/tmp/cache/worker_01/`, etc.
- **Graceful Shutdown**: 45-second timeout with proper signal handling

### Worker Environment

Each worker gets:
- **Unique Worker UID**: `worker-XX-{WORKER_TYPE}`
- **Isolated Cache Directory**: `/tmp/cache/worker_XX/`
- **Separate Browser Instance**: Prevents conflicts
- **Individual Log File**: `/tmp/worker_XX.log`

## Management Commands

### Basic Operations
```bash
# Start 2 workers
./scripts/supervisor_macos_clean.sh start 2 KGAI

# Check worker status
./scripts/supervisor_macos_clean.sh status

# Stop all workers
./scripts/supervisor_macos_clean.sh stop

# Restart workers
./scripts/supervisor_macos_clean.sh restart 4 KGAI
```

### Monitoring
```bash
# View available log files
./scripts/supervisor_macos_clean.sh logs

# Tail all worker logs in real-time
./scripts/supervisor_macos_clean.sh tail

# View specific worker log
tail -f /tmp/worker_01.log
```

### Cleanup
```bash
# Clean up all supervisor files and logs
./scripts/supervisor_macos_clean.sh clean
```

## Chrome Process Management

### Automatic Cleanup

The solution automatically handles Chrome browser cleanup:
- **On Worker Shutdown**: Chrome processes are terminated gracefully
- **On Supervisor Stop**: Orphaned Chrome processes are cleaned up
- **Signal Handling**: SIGTERM/SIGINT properly close browsers

### Manual Cleanup

If needed, you can manually clean up Chrome processes:

```bash
# List worker-related Chrome processes
python3 scripts/cleanup_chrome.py --list-only

# Clean up worker-related Chrome processes
python3 scripts/cleanup_chrome.py

# Force cleanup without confirmation
python3 scripts/cleanup_chrome.py --force

# Clean up ALL Chrome processes (use with caution)
python3 scripts/cleanup_chrome.py --all
```

## Scaling Workers

### Horizontal Scaling

To run more workers, simply change the count:

```bash
# Scale up to 8 workers
./scripts/supervisor_macos_clean.sh stop
./scripts/supervisor_macos_clean.sh start 8 KGAI
```

### Resource Considerations

- **Memory**: Each worker uses ~500MB-1GB RAM
- **CPU**: Each worker can use 1-2 CPU cores during active tasks
- **Disk**: Each worker needs ~100MB cache space
- **Network**: Consider proxy limits and rate limiting

**Recommended Limits**:
- **Development**: 2-4 workers
- **Production**: 4-8 workers (depending on hardware)

## Troubleshooting

### Workers Not Starting

1. **Check supervisor status**:
   ```bash
   ./scripts/supervisor_macos_clean.sh status
   ```

2. **Check worker logs**:
   ```bash
   tail -20 /tmp/worker_00.log
   ```

3. **Check supervisor logs**:
   ```bash
   tail -20 /tmp/supervisord.log
   ```

### Orphaned Chrome Processes

1. **List Chrome processes**:
   ```bash
   python3 scripts/cleanup_chrome.py --list-only
   ```

2. **Clean up manually**:
   ```bash
   python3 scripts/cleanup_chrome.py --force
   ```

### Workers Crashing

1. **Check Redis connection**:
   ```bash
   redis-cli ping
   ```

2. **Check cache directories**:
   ```bash
   ls -la /tmp/cache/
   ```

3. **Restart with clean state**:
   ```bash
   ./scripts/supervisor_macos_clean.sh clean
   ./scripts/supervisor_macos_clean.sh start 2 KGAI
   ```

## File Structure

After cleanup, the supervisor solution uses these files:

```
supervisor/
├── supervisord.conf              # Main supervisor configuration

scripts/
├── supervisor_macos_clean.sh     # Enhanced management script
├── worker_wrapper.py             # Worker startup wrapper
└── cleanup_chrome.py             # Chrome cleanup utility

docs/
├── SUPERVISOR_MULTI_WORKER_GUIDE.md  # This guide
├── BROWSER_CLEANUP_SOLUTION.md       # Technical details
└── MACOS_SUPERVISOR_ISSUES.md        # macOS-specific notes
```

## Production Deployment

For production environments:

1. **Use systemd** (Linux) or **launchd** (macOS) to auto-start supervisor
2. **Monitor logs** with log rotation
3. **Set resource limits** in supervisor configuration
4. **Use health checks** to monitor worker status
5. **Implement alerting** for worker failures

### Example systemd Service (Linux)

```ini
[Unit]
Description=Selenium Worker Supervisor
After=network.target

[Service]
Type=forking
User=selenium
Environment=WORKER_COUNT=4
Environment=WORKER_TYPE=KGAI
ExecStart=/usr/local/bin/supervisord -c /app/supervisor/supervisord.conf
ExecStop=/usr/local/bin/supervisorctl -c /app/supervisor/supervisord.conf shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

This supervisor solution provides a robust, scalable, and maintainable approach to running multiple selenium workers with proper resource management and cleanup.
