# macOS Supervisor Issues and Solutions

## The kqueue Error

When running supervisor on macOS, you may see this error during shutdown:

```
error: uncaptured python exception, closing channel <supervisor.http.deferring_http_channel connected '' at 0x102256c10 channel#: 2 requests:1> (<class 'FileNotFoundError'>:[Errno 2] No such file or directory [/opt/homebrew/Cellar/supervisor/4.3.0/libexec/lib/python3.13/site-packages/supervisor/supervisord.py|runforever|243] [/opt/homebrew/Cellar/supervisor/4.3.0/libexec/lib/python3.13/site-packages/supervisor/poller.py|unregister_writable|177] [/opt/homebrew/Cellar/supervisor/4.3.0/libexec/lib/python3.13/site-packages/supervisor/poller.py|_kqueue_control|181])
```

## What Causes This

This is a **known issue** with supervisor on macOS related to the kqueue polling mechanism. It happens because:

1. **kqueue vs select**: macOS uses kqueue for event polling, but supervisor's implementation has edge cases
2. **File descriptor cleanup**: During shutdown, supervisor tries to clean up file descriptors that may already be closed
3. **Race condition**: The error occurs during the shutdown process and doesn't affect functionality

## Impact

- ⚠️ **Cosmetic only**: The error is harmless and doesn't affect worker functionality
- ✅ **Workers run fine**: All workers start, run, and stop correctly
- ✅ **Auto-restart works**: Process monitoring and restart functionality is unaffected
- ⚠️ **Ugly logs**: The error messages make logs look messy

## Solutions

### Solution 1: Use the Clean Script (Recommended)

Use the enhanced management script that filters out the error messages:

```bash
# Use the clean version that hides kqueue errors
./scripts/supervisor_macos_clean.sh start 4 KGAI
./scripts/supervisor_macos_clean.sh status
./scripts/supervisor_macos_clean.sh stop
```

**Benefits**:
- ✅ Filters out kqueue error messages
- ✅ Better error handling and status checking
- ✅ Clean, readable output
- ✅ All supervisor functionality preserved

### Solution 2: Use Python Launcher (Alternative)

If supervisor issues become problematic, use the Python launcher instead:

```bash
# No supervisor dependencies, pure Python
python3 scripts/launch_workers.py --workers 4 --worker-type KGAI
```

**Benefits**:
- ✅ No macOS-specific issues
- ✅ Cross-platform compatibility
- ✅ Process monitoring and restart
- ✅ Simpler dependency management

### Solution 3: Ignore the Error

If you don't mind the error messages, just use supervisor normally:

```bash
# Standard supervisor usage (with ugly error messages)
export WORKER_COUNT=4 WORKER_TYPE=KGAI
supervisord -c supervisor/supervisord.conf
```

## Comparison

| Approach | Pros | Cons |
|----------|------|------|
| **Clean Script** | ✅ Clean output<br>✅ All supervisor features<br>✅ Easy to use | ⚠️ Extra wrapper layer |
| **Python Launcher** | ✅ No macOS issues<br>✅ Cross-platform<br>✅ Simple | ⚠️ Different interface |
| **Ignore Error** | ✅ Standard supervisor<br>✅ No changes needed | ❌ Ugly error messages |

## Recommendation

For **macOS development**: Use `./scripts/supervisor_macos_clean.sh`

For **production/Docker**: Use standard supervisor (the error doesn't occur in Linux containers)

For **cross-platform**: Use `python3 scripts/launch_workers.py`

## Technical Details

The kqueue error occurs in supervisor's polling mechanism:

1. **Event Loop**: Supervisor uses kqueue on macOS for event polling
2. **Shutdown Race**: During shutdown, file descriptors are closed while kqueue is still polling
3. **Error Handling**: Supervisor doesn't gracefully handle this specific race condition
4. **Upstream Issue**: This is a known issue in supervisor's codebase

The error doesn't affect functionality because it occurs **after** all workers have been properly shut down.

## Future Improvements

Potential fixes that could be implemented:

1. **Patch supervisor**: Contribute a fix to supervisor's kqueue handling
2. **Alternative poller**: Configure supervisor to use select instead of kqueue
3. **Error suppression**: Add better error handling in supervisor configuration

For now, the clean script provides the best user experience on macOS.
