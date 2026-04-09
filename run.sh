#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_DIR="$RUNTIME_DIR/pids"
STATE_DIR="$RUNTIME_DIR/state"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_REQ_STAMP_FILE="$STATE_DIR/backend_requirements.sha256"
FRONTEND_LOCK_STAMP_FILE="$STATE_DIR/frontend_package_lock.sha256"
BACKEND_RUNTIME_PORT_FILE="$STATE_DIR/backend_runtime_port"
FRONTEND_RUNTIME_PORT_FILE="$STATE_DIR/frontend_runtime_port"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

mkdir -p "$LOG_DIR" "$PID_DIR" "$STATE_DIR"

info() { echo "[matopt] $*"; }
warn() { echo "[matopt] $*" >&2; }

require_layout() {
  if [[ ! -d "$BACKEND_DIR" || ! -d "$FRONTEND_DIR" ]]; then
    warn "expected backend/ and frontend/ under $ROOT_DIR"
    exit 1
  fi
}

pid_is_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

pid_cmdline() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

listener_pid_for_port() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

port_in_use() {
  local port="$1"
  local pid
  pid="$(listener_pid_for_port "$port")"
  [[ -n "$pid" ]]
}

read_pid() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file" || true
}

write_pid() {
  local file="$1"
  local pid="$2"
  echo "$pid" > "$file"
}

remove_pid() {
  local file="$1"
  rm -f "$file"
}

ensure_backend_venv() {
  if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
    info "creating backend virtualenv"
    python3 -m venv "$BACKEND_DIR/.venv"
  fi
}

sha256_file() {
  local file="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  else
    sha256sum "$file" | awk '{print $1}'
  fi
}

read_stamp() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file" || true
}

write_stamp() {
  local file="$1"
  local value="$2"
  echo "$value" > "$file"
}

backend_requirements_changed() {
  local current saved
  current="$(sha256_file "$BACKEND_DIR/requirements.txt")"
  saved="$(read_stamp "$BACKEND_REQ_STAMP_FILE")"
  [[ "$current" != "$saved" ]]
}

frontend_lock_changed() {
  local lock_file="$FRONTEND_DIR/package-lock.json"
  if [[ ! -f "$lock_file" ]]; then
    return 0
  fi
  local current saved
  current="$(sha256_file "$lock_file")"
  saved="$(read_stamp "$FRONTEND_LOCK_STAMP_FILE")"
  [[ "$current" != "$saved" ]]
}

backend_deps_healthy() {
  # shellcheck disable=SC1091
  source "$BACKEND_DIR/.venv/bin/activate"
  python - <<'PY' >/dev/null 2>&1
import importlib.util
mods = ["fastapi", "uvicorn", "openai", "multipart", "fitz", "docx", "pptx", "PIL", "dotenv"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
raise SystemExit(1 if missing else 0)
PY
}

frontend_deps_healthy() {
  [[ -d "$FRONTEND_DIR/node_modules" && -x "$FRONTEND_DIR/node_modules/.bin/vite" ]]
}

ensure_backend_deps() {
  ensure_backend_venv
  if backend_deps_healthy && ! backend_requirements_changed; then
    info "backend dependencies: already installed"
    return
  fi

  # shellcheck disable=SC1091
  source "$BACKEND_DIR/.venv/bin/activate"
  info "installing backend dependencies"
  pip install --upgrade -r "$BACKEND_DIR/requirements.txt"
  write_stamp "$BACKEND_REQ_STAMP_FILE" "$(sha256_file "$BACKEND_DIR/requirements.txt")"
}

ensure_frontend_deps() {
  if frontend_deps_healthy && ! frontend_lock_changed; then
    info "frontend dependencies: already installed"
    return
  fi

  info "installing frontend dependencies"
  (cd "$FRONTEND_DIR" && npm install)
  if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
    write_stamp "$FRONTEND_LOCK_STAMP_FILE" "$(sha256_file "$FRONTEND_DIR/package-lock.json")"
  fi
}

ensure_deps() {
  ensure_backend_deps
  ensure_frontend_deps
}

next_free_port() {
  local p="$1"
  while port_in_use "$p"; do
    p=$((p + 1))
  done
  echo "$p"
}

write_runtime_ports() {
  echo "$BACKEND_PORT" > "$BACKEND_RUNTIME_PORT_FILE"
  echo "$FRONTEND_PORT" > "$FRONTEND_RUNTIME_PORT_FILE"
}

read_runtime_port() {
  local file="$1"
  local fallback="$2"
  if [[ -f "$file" ]]; then
    cat "$file"
  else
    echo "$fallback"
  fi
}

frontend_port_from_log() {
  local line port
  line="$(grep -Eo 'http://localhost:[0-9]+' "$LOG_DIR/frontend.log" 2>/dev/null | tail -n 1 || true)"
  port="${line##*:}"
  if [[ -n "$port" ]]; then
    echo "$port"
  fi
}

start_backend() {
  local pid listener_pid
  pid="$(read_pid "$BACKEND_PID_FILE")"
  if pid_is_running "$pid"; then
    info "backend already running (pid: $pid)"
    return
  fi
  remove_pid "$BACKEND_PID_FILE"

  info "starting backend"
  (
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1091
    source "$BACKEND_DIR/.venv/bin/activate"
    exec uvicorn main:app --reload --port "$BACKEND_PORT" --env-file .env
  ) >> "$LOG_DIR/backend.log" 2>&1 &

  write_pid "$BACKEND_PID_FILE" "$!"
  sleep 1.2
  listener_pid="$(listener_pid_for_port "$BACKEND_PORT")"
  if [[ -n "$listener_pid" ]]; then
    write_pid "$BACKEND_PID_FILE" "$listener_pid"
    return
  fi

  pid="$(read_pid "$BACKEND_PID_FILE")"
  if ! pid_is_running "$pid"; then
    remove_pid "$BACKEND_PID_FILE"
    warn "backend failed to start; recent log:"
    tail -n 40 "$LOG_DIR/backend.log" >&2 || true
    return 1
  fi
}

start_frontend() {
  local pid listener_pid
  pid="$(read_pid "$FRONTEND_PID_FILE")"
  if pid_is_running "$pid"; then
    info "frontend already running (pid: $pid)"
    return
  fi
  remove_pid "$FRONTEND_PID_FILE"

  info "starting frontend"
  (
    cd "$FRONTEND_DIR"
    VITE_BACKEND_URL="http://localhost:$BACKEND_PORT" exec npm run dev -- --port "$FRONTEND_PORT" --strictPort
  ) >> "$LOG_DIR/frontend.log" 2>&1 &

  write_pid "$FRONTEND_PID_FILE" "$!"
  sleep 1.2
  listener_pid="$(listener_pid_for_port "$FRONTEND_PORT")"
  if [[ -n "$listener_pid" ]]; then
    write_pid "$FRONTEND_PID_FILE" "$listener_pid"
    return
  fi

  pid="$(read_pid "$FRONTEND_PID_FILE")"
  if ! pid_is_running "$pid"; then
    remove_pid "$FRONTEND_PID_FILE"
    warn "frontend failed to start; recent log:"
    tail -n 40 "$LOG_DIR/frontend.log" >&2 || true
    return 1
  fi
}

stop_one() {
  local name="$1"
  local file="$2"
  local port="$3"
  local pid listener_pid
  pid="$(read_pid "$file")"
  listener_pid="$(listener_pid_for_port "$port")"

  if [[ -n "$listener_pid" ]]; then
    pid="$listener_pid"
  fi

  if ! pid_is_running "$pid"; then
    info "$name is not running"
    remove_pid "$file"
    return
  fi

  info "stopping $name (pid: $pid)"
  kill "$pid" 2>/dev/null || true

  for _ in {1..20}; do
    if ! pid_is_running "$pid"; then
      remove_pid "$file"
      return
    fi
    sleep 0.2
  done

  warn "$name did not stop in time, forcing"
  kill -9 "$pid" 2>/dev/null || true
  remove_pid "$file"
}

status() {
  local bpid fpid bport fport blisten flisten log_port
  bport="$(read_runtime_port "$BACKEND_RUNTIME_PORT_FILE" "$BACKEND_PORT")"
  fport="$(read_runtime_port "$FRONTEND_RUNTIME_PORT_FILE" "$FRONTEND_PORT")"
  bpid="$(read_pid "$BACKEND_PID_FILE")"
  fpid="$(read_pid "$FRONTEND_PID_FILE")"
  blisten="$(listener_pid_for_port "$bport")"
  flisten="$(listener_pid_for_port "$fport")"

  if [[ -z "$flisten" ]]; then
    log_port="$(frontend_port_from_log)"
    if [[ -n "$log_port" ]]; then
      flisten="$(listener_pid_for_port "$log_port")"
      if [[ -n "$flisten" ]]; then
        fport="$log_port"
        write_stamp "$FRONTEND_RUNTIME_PORT_FILE" "$fport"
      fi
    fi
  fi

  if [[ -n "$blisten" ]]; then
    info "backend: running (pid: $blisten)"
    write_pid "$BACKEND_PID_FILE" "$blisten"
  else
    info "backend: stopped"
  fi

  if [[ -n "$flisten" ]]; then
    info "frontend: running (pid: $flisten)"
    write_pid "$FRONTEND_PID_FILE" "$flisten"
  else
    info "frontend: stopped"
  fi

  info "frontend url: http://localhost:$fport"
  info "backend url:  http://localhost:$bport"
  info "logs: $LOG_DIR"
}

start() {
  require_layout
  ensure_deps
  if port_in_use "$BACKEND_PORT"; then
    local chosen_backend
    chosen_backend="$(next_free_port "$BACKEND_PORT")"
    warn "backend port $BACKEND_PORT is busy, using $chosen_backend"
    BACKEND_PORT="$chosen_backend"
  fi
  if port_in_use "$FRONTEND_PORT"; then
    local chosen_frontend
    chosen_frontend="$(next_free_port "$FRONTEND_PORT")"
    warn "frontend port $FRONTEND_PORT is busy, using $chosen_frontend"
    FRONTEND_PORT="$chosen_frontend"
  fi
  write_runtime_ports
  start_backend
  start_frontend
  status
}

stop() {
  local bport fport
  bport="$(read_runtime_port "$BACKEND_RUNTIME_PORT_FILE" "$BACKEND_PORT")"
  fport="$(read_runtime_port "$FRONTEND_RUNTIME_PORT_FILE" "$FRONTEND_PORT")"
  stop_one "frontend" "$FRONTEND_PID_FILE" "$fport"
  stop_one "backend" "$BACKEND_PID_FILE" "$bport"
}

restart() {
  stop
  start
}

logs() {
  touch "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
  info "showing logs (Ctrl+C to exit)"
  tail -n 80 -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
}

audit() {
  require_layout
  ensure_frontend_deps
  info "running frontend npm audit"
  (cd "$FRONTEND_DIR" && npm audit)
}

audit_fix() {
  require_layout
  ensure_frontend_deps
  info "running frontend npm audit fix"
  (cd "$FRONTEND_DIR" && npm audit fix)
}

usage() {
  cat <<EOF
MatOpt process manager

Usage:
  run.sh start     Install deps and start backend + frontend
  run.sh stop      Stop backend + frontend
  run.sh restart   Restart backend + frontend
  run.sh status    Show current status
  run.sh logs      Follow backend + frontend logs
  run.sh audit     Run npm audit in frontend
  run.sh audit-fix Run npm audit fix in frontend
EOF
}

main() {
  local cmd="${1:-start}"
  case "$cmd" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    logs) logs ;;
    audit) audit ;;
    audit-fix) audit_fix ;;
    -h|--help|help) usage ;;
    *)
      warn "unknown command: $cmd"
      usage
      exit 1
      ;;
  esac
}

main "$@"
