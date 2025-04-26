#!/bin/bash
# service.sh - Service management framework for WebProtege container
# 
# This framework provides a standardized way to manage services within the container
# including starting, stopping, and checking status of services.

# Constants
SERVICE_ROOT="/var/run/webprotege"
SERVICE_TIMEOUT=30
DEBUG=${DEBUG:-false}

# Global service registry
declare -A SERVICES=()
declare -A SERVICE_PIDS=()
declare -A SERVICE_DEPS=()
declare -A SERVICE_STATUS=()

# Ensure service directory exists
mkdir -p "${SERVICE_ROOT}"

# Logging function with consistent format
log() {
  local level="$1"
  local message="$2"
  local service="${3:-system}"
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] [${level}] [${service}] ${message}"
}

# Debug logging
debug() {
  if [ "$DEBUG" = "true" ]; then
    log "DEBUG" "$1" "$2"
  fi
}

# Initialize the service framework
init_services() {
  debug "Initializing service framework"
  mkdir -p "${SERVICE_ROOT}"
  
  # Set up signal handlers
  trap handle_sigterm SIGTERM
  trap handle_sigint SIGINT
  
  # Create base status file
  echo "initialized" > "${SERVICE_ROOT}/system.status"
}

# Signal handlers
handle_sigterm() {
  log "INFO" "Received SIGTERM, shutting down all services" "system"
  stop_all_services
  exit 0
}

handle_sigint() {
  log "INFO" "Received SIGINT, shutting down all services" "system"
  stop_all_services
  exit 0
}

# Register a service with the framework
# Usage: register_service name command [depends_on...]
register_service() {
  local name="$1"
  local command="$2"
  shift 2
  local deps=("$@")
  
  debug "Registering service: ${name}" "system"
  
  SERVICES["$name"]="$command"
  SERVICE_DEPS["$name"]="${deps[*]}"
  SERVICE_STATUS["$name"]="registered"
  
  # Create service directory
  mkdir -p "${SERVICE_ROOT}/${name}"
  echo "registered" > "${SERVICE_ROOT}/${name}/status"
  
  debug "Service registered: ${name} (deps: ${SERVICE_DEPS["$name"]})" "system"
}

# Start a specific service
# Usage: start_service name
start_service() {
  local name="$1"
  local force="${2:-false}"
  
  # Check if service exists
  if [ -z "${SERVICES[$name]}" ]; then
    log "ERROR" "Service not found: ${name}" "system"
    return 1
  fi
  
  # Check if service is already running
  if [ "${SERVICE_STATUS[$name]}" = "running" ] && [ "$force" != "true" ]; then
    log "INFO" "Service already running: ${name}" "system"
    return 0
  fi
  
  log "INFO" "Starting service: ${name}" "$name"
  
  # Check dependencies
  local deps="${SERVICE_DEPS[$name]}"
  if [ -n "$deps" ]; then
    debug "Service ${name} has dependencies: ${deps}" "$name"
    for dep in $deps; do
      if [ "${SERVICE_STATUS[$dep]}" != "running" ]; then
        log "INFO" "Starting dependency: ${dep}" "$name"
        start_service "$dep" || return 1
      fi
    done
  fi
  
  # Execute the service command in background
  local command="${SERVICES[$name]}"
  debug "Executing: ${command}" "$name"
  
  # Execute in subshell with output to log file
  (
    # Create a status file for the service
    echo "starting" > "${SERVICE_ROOT}/${name}/status"
    
    # Execute the command
    eval "$command" > "${SERVICE_ROOT}/${name}/stdout.log" 2> "${SERVICE_ROOT}/${name}/stderr.log" &
    echo $! > "${SERVICE_ROOT}/${name}/pid"
    
    # Mark as running
    echo "running" > "${SERVICE_ROOT}/${name}/status"
    exit 0
  ) &
  
  # Wait for service to start
  local timeout=${SERVICE_TIMEOUT}
  while [ $timeout -gt 0 ]; do
    if [ -f "${SERVICE_ROOT}/${name}/pid" ] && [ "$(cat "${SERVICE_ROOT}/${name}/status")" = "running" ]; then
      SERVICE_PIDS["$name"]=$(cat "${SERVICE_ROOT}/${name}/pid")
      SERVICE_STATUS["$name"]="running"
      log "INFO" "Service started successfully (PID: ${SERVICE_PIDS[$name]})" "$name"
      return 0
    fi
    sleep 1
    timeout=$((timeout - 1))
  done
  
  # If we got here, the service didn't start properly
  log "ERROR" "Service failed to start within timeout" "$name"
  SERVICE_STATUS["$name"]="failed"
  echo "failed" > "${SERVICE_ROOT}/${name}/status"
  return 1
}

# Stop a specific service
# Usage: stop_service name
stop_service() {
  local name="$1"
  
  # Check if service exists
  if [ -z "${SERVICES[$name]}" ]; then
    log "ERROR" "Service not found: ${name}" "system"
    return 1
  fi
  
  # Check if service is actually running
  if [ "${SERVICE_STATUS[$name]}" != "running" ]; then
    log "INFO" "Service not running: ${name}" "system"
    return 0
  fi
  
  log "INFO" "Stopping service: ${name}" "$name"
  
  # Get PID file
  local pid_file="${SERVICE_ROOT}/${name}/pid"
  if [ ! -f "$pid_file" ]; then
    log "WARNING" "PID file not found, service may have crashed" "$name"
    SERVICE_STATUS["$name"]="stopped"
    echo "stopped" > "${SERVICE_ROOT}/${name}/status"
    return 0
  fi
  
  # Get PID
  local pid=$(cat "$pid_file")
  if [ -z "$pid" ]; then
    log "WARNING" "Empty PID file" "$name"
    SERVICE_STATUS["$name"]="stopped"
    echo "stopped" > "${SERVICE_ROOT}/${name}/status"
    return 0
  fi
  
  # Check if process exists
  if ! kill -0 "$pid" 2>/dev/null; then
    log "WARNING" "Process not found (PID: ${pid}), service may have crashed" "$name"
    SERVICE_STATUS["$name"]="stopped"
    echo "stopped" > "${SERVICE_ROOT}/${name}/status"
    return 0
  fi
  
  # Try gentle stop first
  kill -TERM "$pid" 2>/dev/null
  
  # Wait for process to exit
  local timeout=${SERVICE_TIMEOUT}
  while [ $timeout -gt 0 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      log "INFO" "Service stopped successfully" "$name"
      SERVICE_STATUS["$name"]="stopped"
      echo "stopped" > "${SERVICE_ROOT}/${name}/status"
      return 0
    fi
    sleep 1
    timeout=$((timeout - 1))
  done
  
  # If we got here, need to force kill
  log "WARNING" "Service did not exit gracefully, forcing stop" "$name"
  kill -9 "$pid" 2>/dev/null
  
  # Update status
  SERVICE_STATUS["$name"]="stopped"
  echo "stopped" > "${SERVICE_ROOT}/${name}/status"
  return 0
}

# Restart a service
# Usage: restart_service name
restart_service() {
  local name="$1"
  
  log "INFO" "Restarting service: ${name}" "$name"
  stop_service "$name"
  start_service "$name"
}

# Get status of a service
# Usage: get_service_status name
get_service_status() {
  local name="$1"
  
  # Check if service exists
  if [ -z "${SERVICES[$name]}" ]; then
    log "ERROR" "Service not found: ${name}" "system"
    return 1
  fi
  
  # Get status file
  local status_file="${SERVICE_ROOT}/${name}/status"
  if [ ! -f "$status_file" ]; then
    echo "unknown"
    return 0
  fi
  
  # Get status
  local status=$(cat "$status_file")
  echo "$status"
  
  # If status is running, validate PID
  if [ "$status" = "running" ]; then
    local pid_file="${SERVICE_ROOT}/${name}/pid"
    if [ ! -f "$pid_file" ]; then
      log "WARNING" "PID file not found, updating status to failed" "$name"
      echo "failed" > "$status_file"
      SERVICE_STATUS["$name"]="failed"
      return 0
    fi
    
    local pid=$(cat "$pid_file")
    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
      log "WARNING" "Process not found (PID: ${pid}), updating status to failed" "$name"
      echo "failed" > "$status_file"
      SERVICE_STATUS["$name"]="failed"
      return 0
    fi
  fi
  
  return 0
}

# Start all registered services
# Usage: start_all_services
start_all_services() {
  log "INFO" "Starting all services" "system"
  
  for name in "${!SERVICES[@]}"; do
    start_service "$name"
  done
}

# Stop all registered services
# Usage: stop_all_services
stop_all_services() {
  log "INFO" "Stopping all services" "system"
  
  # Create a reversed list of services to stop dependencies last
  local service_list=()
  for name in "${!SERVICES[@]}"; do
    service_list+=("$name")
  done
  
  # Stop in reverse order (dependencies last)
  for ((i=${#service_list[@]}-1; i>=0; i--)); do
    local name="${service_list[$i]}"
    stop_service "$name"
  done
}

# Get status of all services
# Usage: get_all_services_status
get_all_services_status() {
  log "INFO" "Checking status of all services" "system"
  
  local all_ok=true
  
  for name in "${!SERVICES[@]}"; do
    local status=$(get_service_status "$name")
    echo "${name}: ${status}"
    
    if [ "$status" != "running" ]; then
      all_ok=false
    fi
  done
  
  if [ "$all_ok" = true ]; then
    return 0
  else
    return 1
  fi
}

# Monitor all services and restart if needed
# Usage: monitor_services
monitor_services() {
  log "INFO" "Starting service monitor" "system"
  
  while true; do
    for name in "${!SERVICES[@]}"; do
      local status=$(get_service_status "$name")
      if [ "$status" = "failed" ]; then
        log "WARNING" "Service failed, attempting restart" "$name"
        restart_service "$name"
      fi
    done
    
    sleep 10
  done
}

# Export functions
export -f register_service
export -f start_service
export -f stop_service
export -f restart_service
export -f get_service_status
export -f start_all_services
export -f stop_all_services
export -f get_all_services_status
export -f monitor_services
export -f log
export -f debug

# Initialize on sourcing
init_services