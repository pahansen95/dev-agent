#!/bin/bash
set -e

# If we're in debug mode, always return healthy
if [ "${DEBUG_MODE}" = "true" ]; then
  echo "DEBUG MODE: Always reporting healthy"
  exit 0
fi

# Check if Tomcat is running
if ! pgrep -f "java.*catalina" > /dev/null; then
  echo "Tomcat is not running"
  exit 1
fi

# Check if MongoDB is running
if ! pgrep mongod > /dev/null; then
  echo "MongoDB is not running"
  exit 1
fi

# Check if WebProtege is responding
if ! curl -s --fail http://localhost:8080/webprotege > /dev/null; then
  echo "WebProtege is not responding"
  exit 1
fi

# All checks passed
exit 0