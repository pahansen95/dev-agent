#!/bin/bash
# Set proper system properties for Tomcat and WebProtege
export CATALINA_OPTS="$CATALINA_OPTS -Dfile.encoding=UTF-8 -Dwebprotege.config.directory=/etc/webprotege -Ddata.directory=/srv/webprotege"