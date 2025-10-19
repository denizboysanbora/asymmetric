#!/bin/bash
# Unified Analyst - Single script to manage all analyst functionality
# Replaces all individual start/stop/status scripts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYST_SCRIPT="$SCRIPT_DIR/analyst.py"
PYTHON_PATH="$SCRIPT_DIR/input/alpaca/venv/bin/python3"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/analyst.pid"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to print output
print_status() {
    echo "SUCCESS: $1"
}

print_warning() {
    echo "WARNING: $1"
}

print_error() {
    echo "ERROR: $1"
}

print_info() {
    echo "INFO: $1"
}

# Function to check if analyst is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start analyst
start_analyst() {
    local mode="${1:-breakout}"
    local daemon="${2:-false}"
    local auto_trade="${3:-false}"
    local use_mcp="${4:-false}"
    local max_stocks="${5:-30}"
    local top_n="${6:-10}"
    
    echo "Starting Unified Analyst..."
    echo "Mode: $mode"
    echo "Daemon: $daemon"
    echo "Auto-trade: $auto_trade"
    echo "MCP: $use_mcp"
    echo ""
    
    # Check if already running
    if is_running; then
        print_warning "Analyst is already running (PID: $(cat $PID_FILE))"
        echo "Use '$0 stop' to stop it first"
        exit 1
    fi
    
    # Build command
    local cmd="$PYTHON_PATH $ANALYST_SCRIPT --mode $mode"
    
    if [ "$daemon" = "true" ]; then
        cmd="$cmd --daemon"
    else
        cmd="$cmd --scan"
    fi
    
    if [ "$auto_trade" = "true" ]; then
        cmd="$cmd --auto-trade"
    fi
    
    if [ "$use_mcp" = "true" ]; then
        cmd="$cmd --use-mcp"
    fi
    
    cmd="$cmd --max-stocks $max_stocks --top-n $top_n"
    
    # Start analyst
    if [ "$daemon" = "true" ]; then
        print_info "Starting analyst in daemon mode..."
        nohup $cmd > "$LOG_DIR/analyst.log" 2>&1 &
        local pid=$!
        echo $pid > "$PID_FILE"
        print_status "Analyst started in daemon mode (PID: $pid)"
        print_info "Logs: $LOG_DIR/analyst.log"
    else
        print_info "Running single scan..."
        $cmd
    fi
}

# Function to stop analyst
stop_analyst() {
    echo "Stopping Unified Analyst..."
    
    if is_running; then
        local pid=$(cat "$PID_FILE")
        print_info "Stopping analyst (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 2
        
        if ps -p "$pid" > /dev/null 2>&1; then
            print_warning "Force killing analyst..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
        print_status "Analyst stopped"
    else
        print_warning "Analyst is not running"
    fi
}

# Function to check status
check_status() {
    echo "Unified Analyst Status"
    echo "======================"
    
    if is_running; then
        local pid=$(cat "$PID_FILE")
        print_status "Analyst is running (PID: $pid)"
        
        # Show process info
        echo ""
        print_info "Process Information:"
        ps -p "$pid" -o pid,ppid,cmd,etime,pcpu,pmem 2>/dev/null || true
        
        # Show recent logs
        if [ -f "$LOG_DIR/analyst.log" ]; then
            echo ""
            print_info "Recent Logs (last 10 lines):"
            tail -n 10 "$LOG_DIR/analyst.log" 2>/dev/null || true
        fi
    else
        print_warning "Analyst is not running"
    fi
    
    echo ""
    print_info "Available commands:"
    echo "  $0 start [mode] [daemon] [auto-trade] [use-mcp] [max-stocks] [top-n]"
    echo "  $0 stop"
    echo "  $0 status"
    echo "  $0 scan [mode] [max-stocks] [top-n]"
    echo "  $0 logs"
    echo ""
    echo "Modes: breakout, advanced, mcp"
    echo "Example: $0 start breakout true false false 50 10"
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_DIR/analyst.log" ]; then
        print_info "Showing analyst logs (press Ctrl+C to exit):"
        tail -f "$LOG_DIR/analyst.log"
    else
        print_warning "No log file found at $LOG_DIR/analyst.log"
    fi
}

# Function to run single scan
run_scan() {
    local mode="${1:-breakout}"
    local max_stocks="${2:-30}"
    local top_n="${3:-10}"
    
    echo "Running single scan..."
    echo "Mode: $mode"
    echo "Max stocks: $max_stocks"
    echo "Top N: $top_n"
    echo ""
    
    $PYTHON_PATH $ANALYST_SCRIPT --mode "$mode" --scan --max-stocks "$max_stocks" --top-n "$top_n"
}

# Main command handling
case "${1:-status}" in
    "start")
        start_analyst "${2:-breakout}" "${3:-true}" "${4:-false}" "${5:-false}" "${6:-30}" "${7:-10}"
        ;;
    "stop")
        stop_analyst
        ;;
    "status")
        check_status
        ;;
    "scan")
        run_scan "${2:-breakout}" "${3:-30}" "${4:-10}"
        ;;
    "logs")
        show_logs
        ;;
    "help"|"-h"|"--help")
        echo "Unified Analyst Management Script"
        echo "================================="
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  start [mode] [daemon] [auto-trade] [use-mcp] [max-stocks] [top-n]"
        echo "    Start the analyst"
        echo "    mode: breakout, advanced, mcp (default: breakout)"
        echo "    daemon: true, false (default: true)"
        echo "    auto-trade: true, false (default: false)"
        echo "    use-mcp: true, false (default: false)"
        echo "    max-stocks: number (default: 30)"
        echo "    top-n: number (default: 10)"
        echo ""
        echo "  stop"
        echo "    Stop the analyst"
        echo ""
        echo "  status"
        echo "    Check analyst status"
        echo ""
        echo "  scan [mode] [max-stocks] [top-n]"
        echo "    Run single scan"
        echo ""
        echo "  logs"
        echo "    Show live logs"
        echo ""
        echo "Examples:"
        echo "  $0 start breakout true false false 50 10"
        echo "  $0 scan breakout 30 5"
        echo "  $0 stop"
        echo "  $0 status"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
