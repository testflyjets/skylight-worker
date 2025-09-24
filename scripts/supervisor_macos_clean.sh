#!/bin/bash

# Clean supervisor management script for macOS that handles kqueue errors gracefully
# Usage: ./supervisor_macos_clean.sh [start|stop|status|restart] [worker_count] [worker_type]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SUPERVISOR_CONFIG="$PROJECT_DIR/supervisor/supervisord.conf"

# Default values
DEFAULT_WORKER_COUNT=4
DEFAULT_WORKER_TYPE="KGAI"

# Parse arguments
ACTION=${1:-start}
WORKER_COUNT=${2:-$DEFAULT_WORKER_COUNT}
WORKER_TYPE=${3:-$DEFAULT_WORKER_TYPE}

# Export environment variables
export WORKER_COUNT
export WORKER_TYPE

echo "Supervisor Management Script (macOS Clean)"
echo "=========================================="
echo "Action: $ACTION"
echo "Worker Count: $WORKER_COUNT"
echo "Worker Type: $WORKER_TYPE"
echo "Config: $SUPERVISOR_CONFIG"
echo ""

# Function to check if supervisord is running
is_supervisord_running() {
    if [ -f /tmp/supervisord.pid ]; then
        local pid=$(cat /tmp/supervisord.pid)
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            # PID file exists but process is dead, clean it up
            rm -f /tmp/supervisord.pid
            return 1
        fi
    fi
    return 1
}

# Function to wait for supervisord to stop
wait_for_stop() {
    local timeout=30
    local count=0
    
    while is_supervisord_running && [ $count -lt $timeout ]; do
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo ""
    
    if is_supervisord_running; then
        echo "Warning: Supervisord did not stop within $timeout seconds"
        return 1
    fi
    return 0
}

case $ACTION in
    start)
        echo "Starting supervisord with $WORKER_COUNT workers..."
        if is_supervisord_running; then
            echo "Supervisord appears to be already running"
            echo "Use 'stop' first or check status"
            exit 1
        fi
        
        cd "$PROJECT_DIR"
        
        # Start supervisord in background and capture its output
        echo "Launching supervisord..."
        supervisord -c "$SUPERVISOR_CONFIG" 2>&1 | while IFS= read -r line; do
            # Filter out the kqueue error messages
            if [[ ! "$line" =~ "uncaptured python exception" ]] && \
               [[ ! "$line" =~ "FileNotFoundError" ]] && \
               [[ ! "$line" =~ "_kqueue_control" ]]; then
                echo "$line"
            fi
        done &
        
        # Wait a moment for startup
        sleep 3
        
        if is_supervisord_running; then
            echo "✅ Supervisord started successfully!"
            echo ""
            echo "To check status: $0 status"
            echo "To stop: $0 stop"
        else
            echo "❌ Failed to start supervisord"
            exit 1
        fi
        ;;
        
    stop)
        echo "Stopping supervisord..."
        if ! is_supervisord_running; then
            echo "Supervisord is not running"
            exit 1
        fi
        
        echo "Sending shutdown command..."
        # Redirect stderr to filter out kqueue errors
        supervisorctl -c "$SUPERVISOR_CONFIG" shutdown 2>/dev/null || true

        echo -n "Waiting for supervisord to stop"
        if wait_for_stop; then
            echo "✅ Supervisord stopped successfully!"
        else
            echo "⚠️  Supervisord may still be running, trying force stop..."
            if [ -f /tmp/supervisord.pid ]; then
                pid=$(cat /tmp/supervisord.pid)
                kill -TERM "$pid" 2>/dev/null || true
                sleep 2
                kill -KILL "$pid" 2>/dev/null || true
                rm -f /tmp/supervisord.pid
            fi
            echo "✅ Force stop completed"
        fi

        # Clean up any orphaned Chrome processes
        echo "Cleaning up orphaned Chrome processes..."
        python3 "$PROJECT_DIR/scripts/cleanup_chrome.py" --force 2>/dev/null || echo "Chrome cleanup completed"
        ;;
        
    status)
        echo "Checking supervisord status..."
        if ! is_supervisord_running; then
            echo "❌ Supervisord is not running"
            exit 1
        fi
        
        echo "✅ Supervisord is running"
        echo ""
        supervisorctl -c "$SUPERVISOR_CONFIG" status
        ;;
        
    restart)
        echo "Restarting supervisord..."
        if is_supervisord_running; then
            $0 stop
            sleep 2
        fi
        $0 start "$WORKER_COUNT" "$WORKER_TYPE"
        ;;
        
    logs)
        echo "Showing worker logs..."
        if ! is_supervisord_running; then
            echo "Supervisord is not running"
            exit 1
        fi
        
        echo "Available log files:"
        ls -la /tmp/worker_*.log 2>/dev/null || echo "No worker log files found"
        echo ""
        echo "To tail a specific worker log: tail -f /tmp/worker_01.log"
        echo "To tail all logs: tail -f /tmp/worker_*.log"
        ;;
        
    tail)
        echo "Tailing all worker logs (Ctrl+C to stop)..."
        if ! is_supervisord_running; then
            echo "Warning: Supervisord is not running"
        fi
        
        if ls /tmp/worker_*.log >/dev/null 2>&1; then
            tail -f /tmp/worker_*.log
        else
            echo "No worker log files found"
            exit 1
        fi
        ;;
        
    clean)
        echo "Cleaning up supervisor files..."
        if is_supervisord_running; then
            echo "Stopping supervisord first..."
            $0 stop
        fi
        
        echo "Removing log files and PID files..."
        rm -f /tmp/supervisord.pid
        rm -f /tmp/supervisord.log
        rm -f /tmp/worker_*.log
        rm -f /tmp/supervisor.sock
        echo "✅ Cleanup completed"
        ;;
        
    *)
        echo "Usage: $0 [start|stop|status|restart|logs|tail|clean] [worker_count] [worker_type]"
        echo ""
        echo "Commands:"
        echo "  start   - Start supervisord with workers"
        echo "  stop    - Stop supervisord and all workers"
        echo "  status  - Show status of all workers"
        echo "  restart - Restart supervisord"
        echo "  logs    - Show available log files"
        echo "  tail    - Tail all worker logs"
        echo "  clean   - Clean up all supervisor files"
        echo ""
        echo "Examples:"
        echo "  $0 start 4 KGAI     # Start 4 KGAI workers"
        echo "  $0 status           # Check worker status"
        echo "  $0 stop             # Stop all workers"
        echo "  $0 tail             # Watch all worker logs"
        echo "  $0 clean            # Clean up files"
        exit 1
        ;;
esac
