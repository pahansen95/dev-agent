#!/bin/bash
set -e

# Source service management framework to access its functions
source /opt/webprotege/service.sh

# Color codes for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Testing function
assert() {
  local description="$1"
  local command="$2"
  
  echo -ne "${YELLOW}Testing: ${description}... ${NC}"
  
  if eval "$command"; then
    echo -e "${GREEN}PASS${NC}"
    return 0
  else
    echo -e "${RED}FAIL${NC}"
    return 1
  fi
}

# Print section header
section() {
  echo -e "\n${YELLOW}========== $1 ==========${NC}"
}

# Dump contents of a file for debugging
dump_file() {
  local file="$1"
  if [ -f "$file" ]; then
    echo -e "${YELLOW}Contents of $file:${NC}"
    cat "$file" | sed 's/^/  /'
  else
    echo -e "${RED}File not found: $file${NC}"
  fi
}

# Helper to test for file/dir existence, permissions, and ownership
check_path() {
  local path="$1"
  local expected_owner="$2"
  local expected_group="$3"
  local expected_perms="$4"
  
  if [ ! -e "$path" ]; then
    echo "Path does not exist: $path"
    return 1
  fi
  
  # Get actual values
  local actual_owner=$(stat -c '%U' "$path")
  local actual_group=$(stat -c '%G' "$path")
  local actual_perms=$(stat -c '%a' "$path")
  
  # Check owner
  if [ "$expected_owner" != "$actual_owner" ]; then
    echo "Owner mismatch for $path: expected $expected_owner, got $actual_owner"
    return 1
  fi
  
  # Check group
  if [ "$expected_group" != "$actual_group" ]; then
    echo "Group mismatch for $path: expected $expected_group, got $actual_group"
    return 1
  fi
  
  # Check permissions if specified
  if [ -n "$expected_perms" ] && [ "$expected_perms" != "$actual_perms" ]; then
    echo "Permissions mismatch for $path: expected $expected_perms, got $actual_perms"
    return 1
  fi
  
  return 0
}

# Start tests
section "System Information"
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo "User: $(whoami) ($(id))"
echo "Working directory: $(pwd)"
echo "Java version: $(java -version 2>&1 | head -1)"

section "Directory Structure and Permissions"
assert "WebProtege data directory exists" "[ -d /srv/webprotege ]"
assert "WebProtege config directory exists" "[ -d /etc/webprotege ]"
assert "MongoDB data directory exists" "[ -d /data/db ]"
assert "WebProtege logs directory exists" "[ -d /var/log/webprotege ]"

assert "Data directory permissions" "check_path /srv/webprotege webprotege webprotege 777"
assert "Config directory permissions" "check_path /etc/webprotege webprotege webprotege 777"
assert "MongoDB directory permissions" "check_path /data/db webprotege webprotege ''"

section "Configuration Files"
assert "webprotege.properties exists" "[ -f /etc/webprotege/webprotege.properties ]"
assert "mail.properties exists" "[ -f /etc/webprotege/mail.properties ]"

# Display configuration files
dump_file "/etc/webprotege/webprotege.properties"
dump_file "/etc/webprotege/mail.properties"

section "Application Files"
assert "WebProtege WAR file exists" "[ -f $CATALINA_HOME/webapps/webprotege-server.war ]"
assert "WebProtege CLI exists" "[ -f /opt/webprotege/webprotege-cli.jar ]"

echo "WebProtege WAR file size: $(du -h $CATALINA_HOME/webapps/webprotege-server.war | cut -f1)"
echo "WebProtege CLI file size: $(du -h /opt/webprotege/webprotege-cli.jar | cut -f1)"

section "MongoDB Status"
assert "MongoDB is installed" "which mongod"
assert "MongoDB is running" "pgrep mongod" || echo "MongoDB is not running!"

if pgrep mongod > /dev/null; then
  echo "MongoDB process information:"
  ps -ef | grep mongod | grep -v grep | sed 's/^/  /'
  
  echo "MongoDB listening ports:"
  netstat -tlnp | grep mongo | sed 's/^/  /'
fi

section "Java System Properties"
echo "Current JVM properties for the process:"
java -XX:+PrintFlagsFinal -version 2>&1 | grep -i "system" | sed 's/^/  /'

section "Environment Variables"
echo "Relevant environment variables:"
env | grep -E 'WEBPROTEGE|MONGODB|CATALINA|JAVA' | sort | sed 's/^/  /'

section "Test CLI Tool"
echo "Testing WebProtege CLI tool help command:"
java -jar /opt/webprotege/webprotege-cli.jar --help 2>&1 || echo "CLI tool cannot execute help command"

echo "Testing CLI tool with explicit properties:"
java -Dwebprotege.config.directory=/etc/webprotege -Ddata.directory=/srv/webprotege -jar /opt/webprotege/webprotege-cli.jar --help 2>&1 || echo "CLI tool cannot execute help command with properties"

# Add this test for the specific failing command
echo "Testing admin account creation with explicit properties:"
echo -e "testadmin\ntestpassword\ntestpassword" | java -Dwebprotege.config.directory=/etc/webprotege -Ddata.directory=/srv/webprotege -jar /opt/webprotege/webprotege-cli.jar create-admin-account 2>&1 || echo "Admin creation command fails with properties"

# Add a simple diagnostic command class if it doesn't exist
cat > /tmp/DiagnosticCommand.java << 'EOF'
public class DiagnosticCommand {
    public static void main(String[] args) {
        System.out.println("Diagnostic information:");
        System.out.println("webprotege.config.directory: " + System.getProperty("webprotege.config.directory"));
        System.out.println("data.directory: " + System.getProperty("data.directory"));
        System.out.println("user.dir: " + System.getProperty("user.dir"));
        System.out.println("java.class.path: " + System.getProperty("java.class.path"));
    }
}
EOF

echo "Compiling diagnostic command..."
javac /tmp/DiagnosticCommand.java

echo "Running diagnostic command to check system properties:"
java -cp /tmp -Dwebprotege.config.directory=/etc/webprotege -Ddata.directory=/srv/webprotege DiagnosticCommand

section "Log Files"
echo "Recent log entries from WebProtege logs directory:"
find /var/log/webprotege -type f -name "*.log" -exec echo "=== {} ===" \; -exec tail -10 {} \; || echo "No WebProtege log files found"

echo "Recent MongoDB log entries:"
tail -20 /var/log/mongodb/mongod.log 2>/dev/null || echo "MongoDB log file not found"

section "Tomcat Context Files"
echo "Tomcat context files:"
find $CATALINA_HOME/conf/Catalina -type f -exec echo "=== {} ===" \; -exec cat {} \; || echo "No context files found"

# Final summary
section "Service Status"
echo "Service status from the service management framework:"
get_all_services_status | sed 's/^/  /'

# Check service run directories
echo "Service run directories:"
find /var/run/webprotege -type d | sort | sed 's/^/  /'

# Check service logs
echo "Service logs:"
find /var/run/webprotege -name "*.log" -exec echo "=== {} ===" \; -exec tail -10 {} \; 2>/dev/null || echo "  No service logs found"

section "Summary"
echo "Debug assertions completed. Check above for any FAIL messages."