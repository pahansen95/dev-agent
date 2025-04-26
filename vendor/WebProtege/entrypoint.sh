#!/bin/bash
set -e

# Debug mode flag
DEBUG_MODE=${DEBUG_MODE:-false}
# Export it for service scripts
export DEBUG=${DEBUG_MODE}

# Source service management framework
source /opt/webprotege/service.sh
source /opt/webprotege/service-defs.sh

# Setup signal handling for proper container shutdown
trap 'stop_all_services; exit 0' SIGTERM SIGINT

# Verify WAR file exists and has content
if [ ! -s "$CATALINA_HOME/webapps/webprotege-server.war" ]; then
  log "ERROR" "WebProtege WAR file is missing or empty" "system"
  log "ERROR" "File: $CATALINA_HOME/webapps/webprotege-server.war" "system"
  log "ERROR" "Size: $(du -h $CATALINA_HOME/webapps/webprotege-server.war 2>/dev/null || echo 'not found')" "system"
  exit 1
fi

# Initialize configurations
initialize_configs() {
  log "INFO" "Initializing configurations" "system"
  
  # Copy default config files if they don't exist
  if [ ! -f "$WEBPROTEGE_CONFIG_DIR/webprotege.properties" ]; then
    log "INFO" "Initializing webprotege.properties" "system"
    install -m 0644 /opt/webprotege/default-webprotege.properties "$WEBPROTEGE_CONFIG_DIR/webprotege.properties"
  fi
  
  if [ ! -f "$WEBPROTEGE_CONFIG_DIR/mail.properties" ]; then
    log "INFO" "Initializing mail.properties" "system"
    install -m 0644 /opt/webprotege/default-mail.properties "$WEBPROTEGE_CONFIG_DIR/mail.properties"
  fi
  
  # Configure WebProtégé with environment variables if provided
  if [ -n "$WEBPROTEGE_HOST" ]; then
    log "INFO" "Setting WebProtege host to $WEBPROTEGE_HOST" "system"
    sed -i "s/application.host=.*/application.host=${WEBPROTEGE_HOST}/" $WEBPROTEGE_CONFIG_DIR/webprotege.properties
  fi
  
  if [ -n "$WEBPROTEGE_PORT" ]; then
    log "INFO" "Setting WebProtege port to $WEBPROTEGE_PORT" "system"
    sed -i "s/application.port=.*/application.port=${WEBPROTEGE_PORT}/" $WEBPROTEGE_CONFIG_DIR/webprotege.properties
  fi
  
  if [ -n "$WEBPROTEGE_HTTPS" ]; then
    log "INFO" "Setting WebProtege HTTPS to $WEBPROTEGE_HTTPS" "system"
    sed -i "s/application.https.enabled=.*/application.https.enabled=${WEBPROTEGE_HTTPS}/" $WEBPROTEGE_CONFIG_DIR/webprotege.properties
  fi
  
  if [ -n "$MONGODB_HOST" ]; then
    log "INFO" "Setting MongoDB host to $MONGODB_HOST" "system"
    sed -i "s/mongodb.host=.*/mongodb.host=${MONGODB_HOST}/" $WEBPROTEGE_CONFIG_DIR/webprotege.properties
  fi
  
  if [ -n "$MONGODB_PORT" ]; then
    log "INFO" "Setting MongoDB port to $MONGODB_PORT" "system"
    sed -i "s/mongodb.port=.*/mongodb.port=${MONGODB_PORT}/" $WEBPROTEGE_CONFIG_DIR/webprotege.properties
  fi
  
  # Configure mail settings if provided
  if [ -n "$MAIL_SMTP_HOST" ]; then
    log "INFO" "Setting mail SMTP host to $MAIL_SMTP_HOST" "system"
    sed -i "s/mail.smtp.host=.*/mail.smtp.host=${MAIL_SMTP_HOST}/" $WEBPROTEGE_CONFIG_DIR/mail.properties
  fi
  
  if [ -n "$MAIL_SMTP_PORT" ]; then
    log "INFO" "Setting mail SMTP port to $MAIL_SMTP_PORT" "system"
    sed -i "s/mail.smtp.port=.*/mail.smtp.port=${MAIL_SMTP_PORT}/" $WEBPROTEGE_CONFIG_DIR/mail.properties
  fi
  
  if [ -n "$MAIL_SMTP_FROM" ]; then
    log "INFO" "Setting mail SMTP from to $MAIL_SMTP_FROM" "system"
    sed -i "s/mail.smtp.from=.*/mail.smtp.from=${MAIL_SMTP_FROM}/" $WEBPROTEGE_CONFIG_DIR/mail.properties
  fi
  
  if [ -n "$MAIL_SMTP_USER" ]; then
    log "INFO" "Setting mail SMTP user to $MAIL_SMTP_USER" "system"
    sed -i "s/mail.smtp.user=.*/mail.smtp.user=${MAIL_SMTP_USER}/" $WEBPROTEGE_CONFIG_DIR/mail.properties
  fi
  
  if [ -n "$MAIL_SMTP_PASSWORD" ]; then
    log "INFO" "Setting mail SMTP password" "system"
    sed -i "s/mail.smtp.password=.*/mail.smtp.password=${MAIL_SMTP_PASSWORD}/" $WEBPROTEGE_CONFIG_DIR/mail.properties
    sed -i "s/mail.smtp.auth=.*/mail.smtp.auth=true/" $WEBPROTEGE_CONFIG_DIR/mail.properties
  fi
}

# Create Tomcat context file for WebProtege
setup_tomcat_context() {
  log "INFO" "Setting up Tomcat context for WebProtege" "system"
  mkdir -p "$CATALINA_HOME/conf/Catalina/localhost"
  cat > "$CATALINA_HOME/conf/Catalina/localhost/webprotege.xml" << EOF
<Context docBase="$CATALINA_HOME/webapps/webprotege-server.war" path="/webprotege" />
EOF
}

# Create required directories
setup_directories() {
  log "INFO" "Creating required directories" "system"
  mkdir -p "$WEBPROTEGE_DATA_DIR/uploads"
  mkdir -p "$WEBPROTEGE_DATA_DIR/projects"
  mkdir -p "/var/log/mongodb"
  mkdir -p "/var/run/webprotege/healthcheck"
  
  # Set proper permissions
  chown -R webprotege:webprotege "$WEBPROTEGE_DATA_DIR"
  chown -R webprotege:webprotege "/var/log/webprotege"
}

# Display WAR file info
display_war_info() {
  log "INFO" "WebProtege WAR file information:" "system"
  log "INFO" "Path: $CATALINA_HOME/webapps/webprotege-server.war" "system"
  log "INFO" "Size: $(du -h $CATALINA_HOME/webapps/webprotege-server.war)" "system"
  log "INFO" "Context path: /webprotege" "system"
}

# Main function to start the container
main() {
  # Setup necessary parts
  initialize_configs
  setup_tomcat_context
  setup_directories
  display_war_info
  
  # Register all services
  register_all_services
  
  # Check if we're in debug mode
  if [ "$DEBUG_MODE" = "true" ]; then
    log "INFO" "Starting in DEBUG MODE" "system"
    
    # In debug mode, only start MongoDB
    start_service "mongodb"
    start_service "mongodb-check"
    
    # And debug service to keep container running
    start_service "debug"
  else
    log "INFO" "Starting all services" "system"
    
    # Start all services
    start_service "mongodb"
    start_service "mongodb-check"
    start_service "tomcat"
    start_service "webprotege-admin"
    start_service "healthcheck"
  fi
  
  # Start monitoring services in the background
  monitor_services &
  
  # Block and wait for signals
  log "INFO" "Container initialized, waiting for signals" "system"
  
  # Create a simple reaper to handle zombie processes
  while true; do
    wait || true
    sleep 1
  done
}

# Run the main function
main