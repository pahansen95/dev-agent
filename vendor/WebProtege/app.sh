#!/bin/bash
set -eEou pipefail

# Error handling
error_handler() {
  local line="$1"
  local cmd="$2"
  local code="$3"
  echo "Error at line $line (command: $cmd, exit code: $code)" >&2
  exit $code
}
trap 'error_handler ${LINENO} "$BASH_COMMAND" $?' ERR

# Get the script directory in a more portable way
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

CONTEXT="$(get_script_dir)"

# Function to display usage information
usage() {
  cat << EOF
Usage: $0 COMMAND [OPTIONS]

Commands:
  build [OPTIONS]    Build the WebProtege image using docker buildx
                     Additional options are passed directly to buildx
                     Default: --platform linux/amd64 --network=host
  start [--debug]    Start the WebProtege container
                     --debug: Run in debug mode (blocks indefinitely for troubleshooting)
  stop               Stop the WebProtege container
  cleanup            Remove the stopped WebProtege container
  status             Show the status of the WebProtege container
  logs [OPTIONS]     Show logs from the WebProtege container
                     Additional options are passed to docker logs
  shell              Open a shell in the running WebProtege container
  exec COMMAND       Execute a command in a bash shell in the running WebProtege container
                     COMMAND: The shell command to run and any arguments
  sync [OPTIONS]     Sync data between local and remote Docker host
                     All arguments are passed directly to sync.sh
  service COMMAND    Manage services inside the container
                     Commands: status, start, stop, restart
                     Example: $0 service status
  debug              Run diagnostics inside the container

Build Options:
  --platform=<platforms>  Build for specific platforms (default: linux/amd64)
  --network=<network>     Network mode for docker build (default: host)
  --push                  Push to registry after build
  --tag, -t               Name and tag the image (default: webprotege:latest)
  --build-arg=<key>=<value>  Set build-time variables (e.g., MONGODB_VERSION=8.0.8)

Environment Variables:
  WORK_CACHE         (Required) Directory for persistent data storage
  DOCKER_HOST        (Optional) Remote Docker host URL (e.g., ssh://user@host)
  REMOTE_DATA_DIR    (Optional) Path on remote host to store WebProtege data

Examples:
  $0 build                # Uses default options (--platform linux/amd64 --network=host)
  $0 build --platform=linux/amd64,linux/arm64 --tag username/webprotege:latest --push
  $0 build --build-arg MONGODB_VERSION=8.0.9
  $0 start
  $0 logs -f
  $0 exec ls -la /opt/tomcat/webapps

EOF
  exit 1
}

# Configuration
CONTAINER_NAME="webprotege-container"
IMAGE_NAME="webprotege"
PORT_TOMCAT="8080"
PORT_MONGODB="27017"

# Check if WORK_CACHE environment variable is set
if [ -z "${WORK_CACHE:-}" ]; then
  echo "Error: WORK_CACHE environment variable is not set."
  echo "Please set WORK_CACHE to a valid directory path and try again."
  exit 1
fi

# Set up directories
DATA_DIR="$WORK_CACHE/webprotege"
WEBPROTEGE_DATA="$DATA_DIR/data"
WEBPROTEGE_CONFIG="$DATA_DIR/config"
WEBPROTEGE_LOGS="$DATA_DIR/logs"
MONGODB_DATA="$DATA_DIR/mongodb"

# Function to create the necessary directories
create_directories() {
  mkdir -p "$WEBPROTEGE_DATA"
  mkdir -p "$WEBPROTEGE_CONFIG"
  mkdir -p "$WEBPROTEGE_LOGS"
  mkdir -p "$MONGODB_DATA"

  # Create configuration files if they don't exist
  if [ ! -f "$WEBPROTEGE_CONFIG/webprotege.properties" ]; then
    install -m0644 "${CONTEXT}/webprotege.properties" "$WEBPROTEGE_CONFIG/webprotege.properties"
  fi
  
  if [ ! -f "$WEBPROTEGE_CONFIG/mail.properties" ]; then
    install -m0644 "${CONTEXT}/mail.properties" "$WEBPROTEGE_CONFIG/mail.properties"
  fi
}

# Function to build the Docker image using buildx
build_image() {
  echo "Building WebProtege Docker image using buildx..."
  
  # Check if buildx is available
  if ! docker buildx version &>/dev/null; then
    echo "Error: Docker buildx is not available."
    echo "Please make sure you have Docker 19.03 or newer with experimental features enabled."
    exit 1
  fi
  
  # Parse custom arguments for tag
  local build_cmd=("docker" "buildx" "build")
  local custom_tag=""
  local custom_platform_set=false
  local custom_network_set=false
  
  # Process arguments
  while [[ $# -gt 0 ]]; do
    arg="$1"
    # Extract custom tag if specified
    if [[ "$arg" == "--tag="* ]] || [[ "$arg" == "-t="* ]]; then
      custom_tag="${arg#*=}"
      build_cmd+=("$arg")
    elif [[ "$arg" == "--tag" ]] || [[ "$arg" == "-t" ]]; then
      # If the next argument is the tag value
      if [[ $# -gt 1 ]]; then
        custom_tag="$2"
        build_cmd+=("$arg" "$2")
        shift
      else
        echo "Error: --tag option requires a value" >&2
        exit 1
      fi
    elif [[ "$arg" == "--platform="* ]]; then
      custom_platform_set=true
      build_cmd+=("$arg")
    elif [[ "$arg" == "--platform" ]]; then
      custom_platform_set=true
      build_cmd+=("$arg" "$2")
      shift
    elif [[ "$arg" == "--network="* ]]; then
      custom_network_set=true
      build_cmd+=("$arg")
    elif [[ "$arg" == "--network" ]]; then
      custom_network_set=true
      build_cmd+=("$arg" "$2")
      shift
    else
      # Pass all other arguments directly
      build_cmd+=("$arg")
    fi
    shift
  done
  
  # Add default platform if not specified
  if ! $custom_platform_set; then
    build_cmd+=("--platform" "linux/amd64")
  fi
  
  # Add default network if not specified
  if ! $custom_network_set; then
    build_cmd+=("--network=host")
  fi
  
  # Add default tag if not specified
  if [[ -z "$custom_tag" ]]; then
    build_cmd+=("--tag" "$IMAGE_NAME")
  else
    # If custom tag is specified, update IMAGE_NAME for use in container
    IMAGE_NAME="$custom_tag"
  fi
  
  # Add context directory
  build_cmd+=("${CONTEXT}")
  
  echo "Running: ${build_cmd[*]}"
  "${build_cmd[@]}"
  
  echo "Build completed successfully."
}

# Function to start the container
start_container() {
  local debug_mode=false
  
  # Check for debug flag
  if [[ "${1:-}" == "--debug" ]]; then
    debug_mode=true
    echo "Debug mode enabled. Container will run in debug mode with healthcheck always passing."
  fi
  
  create_directories
  
  # Check if container already exists
  if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Container $CONTAINER_NAME already exists."
    
    # Check if it's running
    if docker ps | grep -q "$CONTAINER_NAME"; then
      echo "Container is already running."
      return 0
    else
      echo "Starting existing container..."
      docker start "$CONTAINER_NAME"
      return 0
    fi
  fi
  
  # Check if image exists locally
  if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    echo "Image $IMAGE_NAME does not exist locally."
    echo "Building it now using buildx..."
    build_image
  fi
  
  echo "Starting WebProtege container..."
  
  # Build the basic docker run command
  docker_cmd=("docker" "run")
  
  # Add environment variable for debug mode if needed
  if $debug_mode; then
    docker_cmd+=("-e" "DEBUG_MODE=true")
  fi
  
  # Healthcheck is now defined in the Dockerfile
  
  # Complete the docker run command
  docker_cmd+=("-d" 
    "--name" "$CONTAINER_NAME"
    "-p" "$PORT_TOMCAT:8080"
    "-p" "$PORT_MONGODB:27017"
    "-v" "$WEBPROTEGE_DATA:/srv/webprotege"
    "-v" "$WEBPROTEGE_CONFIG:/etc/webprotege"
    "-v" "$WEBPROTEGE_LOGS:/var/log/webprotege"
    "-v" "$MONGODB_DATA:/data/db"
    "-e" "WEBPROTEGE_ADMIN_USER=admin"
    "-e" "WEBPROTEGE_ADMIN_PASSWORD=admin123"
    "-e" "WEBPROTEGE_HOST=localhost"
    "-e" "WEBPROTEGE_PORT=$PORT_TOMCAT"
    "-e" "WEBPROTEGE_HTTPS=false"
    "-e" "MONGODB_HOST=localhost"
    "-e" "MONGODB_PORT=27017"
    "--restart" "no"
    "$IMAGE_NAME")
  
  # No need for special command in debug mode anymore, handled by entrypoint
  
  # Execute the command
  "${docker_cmd[@]}"
  
  echo "WebProtege is starting..."
  
  if $debug_mode; then
    echo "Container is running in debug mode."
    echo "Connect to it with: docker exec -it $CONTAINER_NAME /bin/bash"
    echo "Once inside the container, you can run:"
    echo "  - 'source /opt/webprotege/service.sh' to use service management commands"
    echo "  - 'get_all_services_status' to check service status"
    echo "  - 'start_service NAME' to start a specific service"
    echo "  - 'stop_service NAME' to stop a specific service"
    echo "  - 'bash /opt/webprotege/debug.sh' to run diagnostics"
  else
    echo "It may take a minute or two for the service to fully initialize."
    echo "You can access it at http://localhost:$PORT_TOMCAT/webprotege"
    echo "Default login: admin/admin123"
  fi
}

# Function to stop the container
stop_container() {
  echo "Stopping WebProtege container..."
  docker stop "$CONTAINER_NAME" || echo "Container not running."
}

# Function to clean up the container
cleanup_container() {
  # Check if container is running
  if docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: Container $CONTAINER_NAME is still running. Stop it first with 'stop' command."
    exit 1
  fi
  
  # Check if container exists
  if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo "Removing container $CONTAINER_NAME..."
    docker rm "$CONTAINER_NAME"
  else
    echo "Container $CONTAINER_NAME does not exist."
  fi
}

# Function to check container status
container_status() {
  if docker ps | grep -q "$CONTAINER_NAME"; then
    echo "WebProtege container is running."
    echo "Access it at http://localhost:$PORT_TOMCAT/webprotege"
    docker ps --filter "name=$CONTAINER_NAME" --format "ID: {{.ID}}\nImage: {{.Image}}\nStatus: {{.Status}}\nPorts: {{.Ports}}"
  else
    echo "WebProtege container is not running."
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
      echo "Container exists but is stopped."
    else
      echo "Container does not exist."
    fi
  fi
}

# Function to display container logs
container_logs() {
  docker logs "$CONTAINER_NAME" "$@"
}

# Function to open a shell in the container
container_shell() {
  docker exec -it "$CONTAINER_NAME" /bin/bash
}

# Function to execute a command in the container
container_exec() {
  if [ $# -eq 0 ]; then
    echo "Error: No command specified for exec" >&2
    echo "Usage: $0 exec COMMAND [ARGS...]" >&2
    exit 1
  fi
  
  docker exec "$CONTAINER_NAME" bash -c "$@"
}

# Function to manage services inside the container
container_service() {
  local command="$1"
  local service_name="${2:-}"
  
  if [ -z "$command" ]; then
    echo "Error: No service command specified" >&2
    echo "Usage: $0 service COMMAND [SERVICE_NAME]" >&2
    echo "Commands: status, start, stop, restart" >&2
    echo "Services: mongodb, tomcat, webprotege-admin, healthcheck" >&2
    exit 1
  fi
  
  case "$command" in
    start|stop|restart)
      if [ -z "$service_name" ]; then
        echo "Error: No service name specified for $command" >&2
        exit 1
      fi
      docker exec "$CONTAINER_NAME" bash -c "source /opt/webprotege/service.sh && ${command}_service $service_name"
      ;;
    status)
      docker exec "$CONTAINER_NAME" bash -c "source /opt/webprotege/service.sh && get_all_services_status"
      ;;
    *)
      echo "Error: Unknown service command: $command" >&2
      echo "Valid commands: status, start, stop, restart" >&2
      exit 1
      ;;
  esac
}

# Main script logic
case "${1:-}" in
  build)
    shift
    build_image "$@"
    ;;
  up|start)
    shift
    start_container "$@"
    ;;
  down|stop)
    stop_container
    ;;
  cleanup|rm|remove)
    cleanup_container
    ;;
  health|status)
    container_status
    ;;
  logs)
    shift
    container_logs "$@"
    ;;
  shell)
    container_shell
    ;;
  exec)
    shift
    container_exec "$@"
    ;;
  service)
    shift
    container_service "$@"
    ;;
  sync)
    shift
    # Call the sync.sh script with all arguments
    "${CONTEXT}/sync.sh" "$@"
    ;;
  debug)
    # Run the debug script in the container
    container_exec "bash /opt/webprotege/debug.sh"
    ;;
  help|*)
    usage
    ;;
esac