#!/bin/bash
# stock-watcher 后台控制脚本
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.monitor.pid"
LOG_FILE="$SCRIPT_DIR/.monitor.log"
PYTHON="/usr/local/bin/python3"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "监控已在运行 (PID: $PID)"
            return 1
        fi
    fi
    echo "启动监控..."
    nohup "$PYTHON" "$SCRIPT_DIR/monitor.py" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "监控已启动 (PID: $(cat $PID_FILE))"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "监控未在运行"
        return 1
    fi
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        echo "监控已停止"
    else
        echo "进程不存在，清理PID文件"
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "监控未运行"
        return 1
    fi
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "监控运行中 (PID: $PID)"
        ps -p "$PID" -o pid,etime,cmd
    else
        echo "PID文件存在但进程已退出"
        rm -f "$PID_FILE"
    fi
}

log() {
    if [ -f "$LOG_FILE" ]; then
        tail -50 "$LOG_FILE"
    else
        echo "暂无日志"
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart)  stop; sleep 1; start ;;
    status)  status ;;
    log)     log ;;
    *) echo "用法: $0 {start|stop|restart|status|log}" ;;
esac
