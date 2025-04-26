#!/bin/bash
# service-defs.sh - Service definitions for WebProtege container
#
# This file defines all the services that run in the WebProtege container

# These functions are sourced by the entrypoint.sh after loading service.sh

# MongoDB service
register_mongodb_service() {
  log "INFO" "Registering MongoDB service" "mongodb"
  
  # Command to run MongoDB
  local cmd="mongod --dbpath ${MONGODB_DATA_DIR} --logpath /var/log/mongodb/mongod.log --fork --logappend"
  
  # Register the service
  register_service "mongodb" "$cmd"
}

# MongoDB check service (verifies MongoDB is ready to accept connections)
register_mongodb_check_service() {
  log "INFO" "Registering MongoDB check service" "mongodb-check"
  
  # Command to check MongoDB is ready
  local check_cmd='
    count=0
    max_attempts=30
    until mongosh --eval "db.adminCommand(\"ping\")" > /dev/null 2>&1; do
      count=$((count + 1))
      if [ $count -ge $max_attempts ]; then
        echo "MongoDB failed to start after $max_attempts attempts" >&2
        exit 1
      fi
      sleep 1
    done
    echo "MongoDB is ready"
    # Keep the service alive
    while true; do
      if ! pgrep mongod > /dev/null; then
        echo "MongoDB process died, exiting check service" >&2
        exit 1
      fi
      sleep 10
    done
  '
  
  # Register the service with dependency on mongodb
  register_service "mongodb-check" "$check_cmd" "mongodb"
}

# Tomcat service
register_tomcat_service() {
  log "INFO" "Registering Tomcat service" "tomcat"
  
  # Command to run Tomcat
  local cmd="cd ${CATALINA_HOME} && catalina.sh run"
  
  # Register the service with dependency on mongodb-check
  register_service "tomcat" "$cmd" "mongodb-check"
}

# WebProtege admin account service
register_webprotege_admin_service() {
  log "INFO" "Registering WebProtege admin account service" "webprotege-admin"
  
  # Only register if admin credentials are provided
  if [ -z "$WEBPROTEGE_ADMIN_USER" ] || [ -z "$WEBPROTEGE_ADMIN_PASSWORD" ]; then
    log "WARNING" "No admin credentials provided, skipping admin creation" "webprotege-admin"
    return 0
  fi
  
  # Command to create admin account
  local cmd='
    # Wait for WebProtege to be accessible
    count=0
    max_attempts=60
    until curl -s "http://localhost:8080/webprotege" > /dev/null 2>&1; do
      count=$((count + 1))
      if [ $count -ge $max_attempts ]; then
        echo "WebProtege failed to start after $max_attempts attempts" >&2
        exit 1
      fi
      sleep 2
    done
    
    # Check if admin already exists
    if [ -f "${WEBPROTEGE_DATA_DIR}/.admin-created" ]; then
      echo "Admin account already exists"
      exit 0
    fi
    
    # Create admin account
    echo "Creating admin account..."
    echo -e "${WEBPROTEGE_ADMIN_USER}\n${WEBPROTEGE_ADMIN_PASSWORD}\n${WEBPROTEGE_ADMIN_PASSWORD}" | \
      java -Dwebprotege.config.directory="${WEBPROTEGE_CONFIG_DIR}" -Ddata.directory="${WEBPROTEGE_DATA_DIR}" \
      -jar /opt/webprotege/webprotege-cli.jar create-admin-account
    
    # Mark admin as created
    touch ${WEBPROTEGE_DATA_DIR}/.admin-created
    echo "Admin account created successfully"
    exit 0
  '
  
  # Register the service with dependency on tomcat
  register_service "webprotege-admin" "$cmd" "tomcat"
}

# Healthcheck service
register_healthcheck_service() {
  log "INFO" "Registering healthcheck service" "healthcheck"
  
  # Command to run healthcheck
  local cmd='
    while true; do
      /usr/local/bin/healthcheck.sh > /var/run/webprotege/healthcheck/status.log 2>&1
      sleep 30
    done
  '
  
  # Register the service with dependencies on mongodb and tomcat (not admin)
  register_service "healthcheck" "$cmd" "mongodb-check" "tomcat"
}

# Debug service - keeps the container running in debug mode
register_debug_service() {
  log "INFO" "Registering debug service" "debug"
  
  # Command to keep container running
  local cmd='
    echo "Debug mode active - container will remain running"
    tail -f /dev/null
  '
  
  # Register the service
  register_service "debug" "$cmd"
}

# Register all services
register_all_services() {
  register_mongodb_service
  register_mongodb_check_service
  register_tomcat_service
  register_webprotege_admin_service
  register_healthcheck_service
  register_debug_service
}

# Export functions
export -f register_mongodb_service
export -f register_mongodb_check_service
export -f register_tomcat_service
export -f register_webprotege_admin_service
export -f register_healthcheck_service
export -f register_debug_service
export -f register_all_services