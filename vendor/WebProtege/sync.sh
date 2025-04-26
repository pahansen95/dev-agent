#!/bin/bash
set -eEou pipefail

#
# WebProtege Data Synchronization Tool
# 
# Synchronizes WebProtege data between local and remote hosts
#

# -------------------- Configuration --------------------

# Default paths and configuration
SYNC_INFO_DIR_NAME="sync-info"
SYNC_FILE_NAME="last_sync"
DEFAULT_DATA_DIR="./data"

# Base rsync options
RSYNC_OPTS=(-avz --no-owner --no-group --delete)

# Define directory structure (table-driven approach)
declare -A DIRS=(
  [data]="data" 
  [config]="config" 
  [logs]="logs" 
  [db]="mongodb"
)

# Script state variables
VERBOSE=false
DRY_RUN=false
FORCE_RM=false
SSH_HOST=""
REMOTE_SUDO=false
COMMAND=""

# Command mapping
declare -A CMD_MAP=(
  [setup]=setup_sync
  [push]=push_data
  [pull]=pull_data
  [sync]=sync_data
  [status]=show_status
  [rm]=remove_remote_dirs
  [help]=usage
)

# Path information
LOCAL_DATA_DIR=""
REMOTE_DATA_DIR=""
declare -A LOCAL_DIRS=()
declare -A REMOTE_DIRS=()
SYNC_DIR=""
SYNC_FILE=""
REMOTE_SYNC_DIR=""
REMOTE_SYNC_FILE=""

# -------------------- Utility Functions --------------------

# Error handling
error_handler() {
  local line="$1"
  local cmd="$2"
  local code="$3"
  echo "Error at line $line (command: $cmd, exit code: $code)" >&2
  exit "$code"
}
trap 'error_handler ${LINENO} "$BASH_COMMAND" $?' ERR

# Get the script directory
get_script_dir() {
  local SOURCE="${BASH_SOURCE[0]}"
  # Resolve $SOURCE until the file is no longer a symlink
  while [ -L "$SOURCE" ]; do
    DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    # If $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
  done
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  echo "$DIR"
}

# Verbosity helper
log() {
  if [ "$VERBOSE" = true ] || [ "${2:-}" = "force" ]; then
    echo "$1"
  fi
}

# Remote command execution with optional sudo
remote_do() {
  if [ "$DRY_RUN" = true ]; then
    if [ "$REMOTE_SUDO" = true ]; then
      log "DRY RUN: Would execute on ${SSH_HOST}: sudo $1"
    else
      log "DRY RUN: Would execute on ${SSH_HOST}: $1"
    fi
    return 0
  fi
  
  # Run the command with sudo if needed
  if [ "$REMOTE_SUDO" = true ]; then
    # Escape single quotes in the command
    local escaped_cmd="${1//\'/\'\\\'\'}"
    ssh "${SSH_HOST}" "sudo bash -c '${escaped_cmd}'"
  else
    ssh "${SSH_HOST}" "$1"
  fi
}

# Check if remote sudo is needed
probe_remote_sudo() {
  log "Checking if sudo is needed on remote host..."
  
  # Try writing to the parent directory of REMOTE_DATA_DIR
  if ! ssh "${SSH_HOST}" "mkdir -p \"$(dirname "${REMOTE_DATA_DIR}")\" && touch \"$(dirname "${REMOTE_DATA_DIR}")/test_perm\" && rm \"$(dirname "${REMOTE_DATA_DIR}")/test_perm\"" 2>/dev/null; then
    log "Need sudo permissions on remote host" force
    REMOTE_SUDO=true
    return 0
  fi
  
  REMOTE_SUDO=false
  return 0
}

# Build paths from base directory
build_paths() {
  local base_dir="$1"
  local target_array="$2"
  
  # Create the main paths for each directory
  for key in "${!DIRS[@]}"; do
    declare -g "${target_array}[$key]=${base_dir}/${DIRS[$key]}"
  done
  
  # Set up sync info directory and file
  if [ "$target_array" = "LOCAL_DIRS" ]; then
    SYNC_DIR="${base_dir}/${SYNC_INFO_DIR_NAME}"
    SYNC_FILE="${SYNC_DIR}/${SYNC_FILE_NAME}"
  else
    REMOTE_SYNC_DIR="${base_dir}/${SYNC_INFO_DIR_NAME}"
    REMOTE_SYNC_FILE="${REMOTE_SYNC_DIR}/${SYNC_FILE_NAME}"
  fi
}

# Create directories locally
create_local_dirs() {
  log "Creating local directories..."
  
  for key in "${!DIRS[@]}"; do
    local dir="${LOCAL_DIRS[$key]}"
    if [ "$DRY_RUN" = true ]; then
      log "DRY RUN: Would create $dir"
    else
      mkdir -p "$dir"
    fi
  done
  
  # Create sync info directory
  if [ "$DRY_RUN" = true ]; then
    log "DRY RUN: Would create $SYNC_DIR"
  else
    mkdir -p "$SYNC_DIR"
    # Create timestamp file if it doesn't exist
    if [ ! -f "$SYNC_FILE" ]; then
      echo "0" > "$SYNC_FILE"
    fi
  fi
}

# Create directories on remote host
create_remote_dirs() {
  log "Creating remote directories..."
  
  # Get remote username to set ownership correctly
  local remote_user
  remote_user=$(ssh "${SSH_HOST}" "whoami")
  log "Remote user is ${remote_user}"
  
  # Create base data directory first with correct permissions
  local parent_dir
  parent_dir=$(dirname "${REMOTE_DATA_DIR}")
  remote_do "install -d -m 0755 ${parent_dir} 2>/dev/null || true"
  remote_do "install -d -m 0755 ${REMOTE_DATA_DIR}"
  
  # Create subdirectories with proper permissions
  for key in "${!DIRS[@]}"; do
    local dir="${REMOTE_DIRS[$key]}"
    remote_do "install -d -m 0755 ${dir}"
  done
  
  # Create sync info directory with proper permissions
  remote_do "install -d -m 0755 ${REMOTE_SYNC_DIR}"
  
  # Create timestamp file if it doesn't exist
  remote_do "touch ${REMOTE_SYNC_FILE} 2>/dev/null || install -D -m 0644 /dev/null ${REMOTE_SYNC_FILE}"
  remote_do "if [ ! -s ${REMOTE_SYNC_FILE} ]; then echo \"0\" > ${REMOTE_SYNC_FILE}; fi"
  
  # Set proper ownership if we used sudo
  if [ "$REMOTE_SUDO" = true ]; then
    log "Setting proper ownership to ${remote_user} for all directories"
    remote_do "chown -R ${remote_user}:${remote_user} ${REMOTE_DATA_DIR}"
    remote_do "chown -R ${remote_user}:${remote_user} ${REMOTE_SYNC_DIR}"
  fi
}

# Sync a directory (push or pull)
sync_dir() {
  local mode="$1"  # push or pull
  local key="$2"
  
  log "Syncing directory: ${key} (${mode})"
  
  local src_dir=""
  local dst_dir=""
  local use_sudo=""
  
  if [ "$mode" = "push" ]; then
    src_dir="${LOCAL_DIRS[$key]}/"
    dst_dir="${SSH_HOST}:${REMOTE_DIRS[$key]}/"
    use_sudo="$REMOTE_SUDO"
  else
    src_dir="${SSH_HOST}:${REMOTE_DIRS[$key]}/"
    dst_dir="${LOCAL_DIRS[$key]}/"
    use_sudo="$REMOTE_SUDO"
  fi
  
  # Build command based on needed permissions
  local rsync_cmd=("rsync" "${RSYNC_OPTS[@]}" "--exclude=${SYNC_INFO_DIR_NAME}")
  
  # Add dry run flag if needed
  if [ "$DRY_RUN" = true ]; then
    rsync_cmd+=("-n")
  fi
  
  # If sudo is needed on remote
  if [ "$use_sudo" = true ]; then
    rsync_cmd+=("-e" "ssh" "--rsync-path=sudo rsync")
  fi
  
  rsync_cmd+=("$src_dir" "$dst_dir")
  
  # Execute rsync
  "${rsync_cmd[@]}"
}

# Update sync timestamps
update_timestamp() {
  if [ "$DRY_RUN" = true ]; then
    log "DRY RUN: Would update timestamps"
    return 0
  fi
  
  local now
  now=$(date +%s)
  echo "$now" > "$SYNC_FILE"
  remote_do "echo \"$now\" > \"${REMOTE_SYNC_FILE}\""
}

# -------------------- Command Functions --------------------

# Display usage information
usage() {
  cat << EOF
Usage: $0 COMMAND [OPTIONS] SSH_HOST [DIR]

A tool for synchronizing WebProtege data between local system and remote host.

Commands:
  setup             Configure sync settings and create required directories
  push              Push local data to remote host
  pull              Pull data from remote host to local system
  sync              Two-way sync between local and remote
  status            Show sync status and last sync time
  rm                Remove remote directories (requires confirmation unless --force is used)
  help              Show this help message

Options:
  -f, --force       Skip confirmation for rm command (use with caution!)
  -v, --verbose     Show more detailed progress information
  -n, --dry-run     Show what would be done without making changes
  -h, --help        Show this help message

Arguments:
  SSH_HOST          The SSH hostname (from your SSH config)
  DIR               Optional local data directory
                    Defaults to $WORK_CACHE/webprotege if WORK_CACHE is set,
                    otherwise defaults to ./data
                    Remote directory will mirror local path structure

Examples:
  # Setup initial configuration
  $0 setup my-ssh-host

  # Push local data to remote
  $0 push my-ssh-host

  # Pull data from remote host to local
  $0 pull my-ssh-host

  # Two-way sync with custom directory
  $0 sync my-ssh-host /path/to/local/data
  
  # Remove remote directories
  $0 rm my-ssh-host
  
  # Dry run to see what would happen
  $0 push --dry-run my-ssh-host

EOF
  exit 1
}

# Setup initial configuration
setup_sync() {
  log "Setting up WebProtege data synchronization with host ${SSH_HOST}..." force
  
  # Create local and remote directories
  create_local_dirs
  probe_remote_sudo
  create_remote_dirs
  
  # Initialize config files if needed
  local script_dir
  script_dir=$(get_script_dir)
  
  if [ ! -f "${LOCAL_DIRS[config]}/webprotege.properties" ] && [ -f "${script_dir}/webprotege.properties" ]; then
    log "Initializing webprotege.properties from template"
    if [ "$DRY_RUN" = false ]; then
      install -m0644 "${script_dir}/webprotege.properties" "${LOCAL_DIRS[config]}/webprotege.properties"
    fi
  fi
  
  if [ ! -f "${LOCAL_DIRS[config]}/mail.properties" ] && [ -f "${script_dir}/mail.properties" ]; then
    log "Initializing mail.properties from template"
    if [ "$DRY_RUN" = false ]; then
      install -m0644 "${script_dir}/mail.properties" "${LOCAL_DIRS[config]}/mail.properties"
    fi
  fi
  
  # Push initial config to remote if needed
  for config_file in "webprotege.properties" "mail.properties"; do
    if [ -f "${LOCAL_DIRS[config]}/${config_file}" ]; then
      # Check if file exists on remote
      if ! ssh "${SSH_HOST}" "test -f \"${REMOTE_DIRS[config]}/${config_file}\"" 2>/dev/null; then
        log "Copying ${config_file} to remote host"
        if [ "$DRY_RUN" = false ]; then
          rsync "${RSYNC_OPTS[@]}" "${LOCAL_DIRS[config]}/${config_file}" "${SSH_HOST}:${REMOTE_DIRS[config]}/"
        fi
      fi
    fi
  done
  
  log "Setup completed successfully!" force
  log "To push local data to remote: $0 push ${SSH_HOST}" force
  log "To pull remote data to local: $0 pull ${SSH_HOST}" force
  log "To sync data both ways: $0 sync ${SSH_HOST}" force
}

# Push local data to remote
push_data() {
  log "Pushing local WebProtege data to ${SSH_HOST}..." force
  
  # Ensure directories exist
  create_local_dirs
  probe_remote_sudo
  create_remote_dirs
  
  # Sync each directory
  for key in "${!DIRS[@]}"; do
    # Skip MongoDB data if container is running on remote
    if [ "$key" = "db" ]; then
      log "Checking if WebProtege is running on remote..."
      if ! ssh "${SSH_HOST}" "! docker ps | grep -q webprotege-container" 2>/dev/null; then
        log "WebProtege is running on remote. Skipping MongoDB data push for safety." force
        log "Stop the container first with: ssh ${SSH_HOST} 'docker stop webprotege-container'" force
        continue
      fi
    fi
    
    sync_dir "push" "$key"
  done
  
  # Update timestamp
  update_timestamp
  
  log "Push completed successfully!" force
}

# Pull remote data to local
pull_data() {
  log "Pulling WebProtege data from ${SSH_HOST}..." force
  
  # Ensure directories exist
  create_local_dirs
  probe_remote_sudo
  create_remote_dirs
  
  # Sync each directory
  for key in "${!DIRS[@]}"; do
    # Skip MongoDB data if container is running locally
    if [ "$key" = "db" ]; then
      log "Checking if WebProtege is running locally..."
      if docker ps | grep -q webprotege-container 2>/dev/null; then
        log "WebProtege is running locally. Skipping MongoDB data pull for safety." force
        log "Stop the container first with: docker stop webprotege-container" force
        continue
      fi
    fi
    
    sync_dir "pull" "$key"
  done
  
  # Update timestamp
  update_timestamp
  
  log "Pull completed successfully!" force
}

# Two-way sync
sync_data() {
  log "Performing two-way sync with ${SSH_HOST}..." force
  pull_data
  push_data
  log "Two-way sync completed successfully!" force
}

# Show sync status
show_status() {
  log "WebProtege Sync Status" force
  log "======================" force
  
  # Ensure directories exist
  create_local_dirs
  
  # Get last sync time
  local last_sync
  last_sync=$(cat "$SYNC_FILE" 2>/dev/null || echo "0")
  local last_sync_date=""
  
  if [ "$last_sync" = "0" ]; then
    last_sync_date="Never"
  else
    last_sync_date=$(date -d "@$last_sync" "+%Y-%m-%d %H:%M:%S")
  fi
  
  # Get container status
  local local_running="No"
  if docker ps | grep -q webprotege-container 2>/dev/null; then
    local_running="Yes"
  fi
  
  local remote_running="No"
  if ssh "${SSH_HOST}" "docker ps | grep -q webprotege-container" 2>/dev/null; then
    remote_running="Yes"
  fi
  
  # Output status
  log "Local data directory: ${LOCAL_DATA_DIR}" force
  log "Remote data directory: ${REMOTE_DATA_DIR} on ${SSH_HOST}" force
  log "Last sync: $last_sync_date" force
  log "" force
  log "WebProtege running locally: $local_running" force
  log "WebProtege running on remote: $remote_running" force
  log "" force
  
  # Directory sizes
  log "Data directory sizes:" force
  for key in "${!DIRS[@]}"; do
    local local_dir="${LOCAL_DIRS[$key]}"
    local remote_dir="${REMOTE_DIRS[$key]}"
    
    local local_size
    local_size=$(du -sh "$local_dir" 2>/dev/null | cut -f1 || echo "N/A")
    
    local remote_size
    remote_size=$(ssh "${SSH_HOST}" "du -sh \"$remote_dir\" 2>/dev/null | cut -f1" || echo "N/A")
    
    log "  $key: Local=${local_size}, Remote=${remote_size}" force
  done
}

# Remove remote directories
remove_remote_dirs() {
  log "WARNING: This will remove all WebProtege data on ${SSH_HOST}" force
  log "Remote directory to be removed: ${REMOTE_DATA_DIR}" force
  
  # Debug output
  echo "DEBUG: FORCE_RM in remove_remote_dirs = $FORCE_RM" >&2
  
  # Skip confirmation if --force flag was used 
  if [ "$FORCE_RM" = true ]; then
    log "Force flag detected, skipping confirmation" "force"
    echo "DEBUG: Force is true, skipping confirmation" >&2
  else
    log "" force
    log "This operation cannot be undone. Please type 'yes' to confirm deletion:" force
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
      log "Deletion cancelled." force
      exit 0
    fi
  fi
  
  # If dry run, just show what would happen
  if [ "$DRY_RUN" = true ]; then
    log "DRY RUN: Would remove directory ${REMOTE_DATA_DIR} on ${SSH_HOST}" force
    return 0
  fi
  
  log "Removing remote directories..." force
  
  # Check if we need sudo
  probe_remote_sudo
  
  # Remove the directory
  remote_do "rm -rf \"${REMOTE_DATA_DIR}\""
  
  log "Remote directories removed successfully." force
}

# -------------------- Main Script Logic --------------------

# Set up default paths based on WORK_CACHE environment variable
if [ -n "${WORK_CACHE:-}" ]; then
  DATA_DIR="$WORK_CACHE/webprotege"
else
  DATA_DIR="$DEFAULT_DATA_DIR"
fi

# Parse command line arguments
parse_args() {
  # Processes arguments and sets global variables
  # Does not run in a subshell to preserve variable values
  
  # Process flags
  while [ $# -gt 0 ]; do
    case "$1" in
      -h|--help)
        usage
        ;;
      -v|--verbose)
        VERBOSE=true
        shift
        ;;
      -n|--dry-run)
        DRY_RUN=true
        shift
        ;;
      -f|--force)
        # Important: Setting global variable
        FORCE_RM=true
        shift
        ;;
      -*)
        echo "Unknown option: $1" >&2
        usage
        ;;
      *)
        # First non-flag argument is the command
        if [ -z "$COMMAND" ]; then
          COMMAND="$1"
          shift
        # Second non-flag argument is the SSH host
        elif [ -z "$SSH_HOST" ]; then
          SSH_HOST="$1"
          shift
        # Third non-flag argument is the data directory
        else
          LOCAL_DATA_DIR="$1"
          shift
        fi
        ;;
    esac
  done
  
  # Command is required
  if [ -z "$COMMAND" ]; then
    echo "Error: No command specified." >&2
    usage
  fi
  
  # Validate command
  if [ -z "${CMD_MAP[$COMMAND]:-}" ]; then
    echo "Error: Unknown command: $COMMAND" >&2
    usage
  fi
  
  # SSH host is required for all commands except help
  if [ -z "$SSH_HOST" ] && [ "$COMMAND" != "help" ]; then
    echo "Error: SSH_HOST is required." >&2
    usage
  fi
  
  # Set default local data directory if not provided
  LOCAL_DATA_DIR="${LOCAL_DATA_DIR:-$DATA_DIR}"
  
  # Make sure LOCAL_DATA_DIR is absolute path
  if [[ "${LOCAL_DATA_DIR}" != /* ]]; then
    LOCAL_DATA_DIR="$(pwd)/${LOCAL_DATA_DIR}"
  fi
  
  # Remote data directory mirrors local structure
  REMOTE_DATA_DIR="${LOCAL_DATA_DIR}"
  
  # Build local and remote paths
  build_paths "$LOCAL_DATA_DIR" "LOCAL_DIRS"
  build_paths "$REMOTE_DATA_DIR" "REMOTE_DIRS"
  
  # For debugging
  echo "DEBUG: FORCE_RM after parsing = $FORCE_RM" >&2
}

# Main entry point
main() {
  # Parse arguments - no subshell to preserve variable changes
  parse_args "$@"
  
  # Print config in verbose mode
  if [ "$VERBOSE" = true ]; then
    log "Command: $COMMAND"
    log "SSH Host: $SSH_HOST"
    log "Local Data Dir: $LOCAL_DATA_DIR"
    log "Remote Data Dir: $REMOTE_DATA_DIR"
    log "Dry Run: $DRY_RUN"
    log "Force: $FORCE_RM"
    log ""
  fi
  
  # For debugging
  echo "DEBUG: FORCE_RM before command = $FORCE_RM" >&2
  
  # Execute the command
  ${CMD_MAP[$COMMAND]}
}

# Start the script
main "$@"