#!/bin/bash
set -e

# Start MongoDB in background
echo "Starting MongoDB..."
mkdir -p /data/db
mongod --fork --logpath /var/log/mongodb/mongod.log

# Wait for MongoDB to start
echo "Waiting for MongoDB to start..."
sleep 5
mongo --eval "db.adminCommand('ping')" > /dev/null 2>&1

# Check if admin account needs to be created
if [ ! -f /srv/webprotege/.admin-account-created ]; then
    echo "WebProtege not yet initialized. Waiting for WebProtege to start..."
    
    # Start Tomcat in background to initialize WebProtege
    catalina.sh start
    
    # Wait for WebProtege to initialize
    RETRY_COUNT=0
    MAX_RETRIES=30
    
    until curl -s "http://localhost:8080/webprotege" > /dev/null || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
        echo "Waiting for WebProtege to start... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT+1))
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "WebProtege failed to start within the expected time."
        exit 1
    fi
    
    # Create admin account if environment variables are set
    if [ -n "$WEBPROTEGE_ADMIN_USER" ] && [ -n "$WEBPROTEGE_ADMIN_PASSWORD" ]; then
        echo "Creating admin account..."
        echo -e "${WEBPROTEGE_ADMIN_USER}\n${WEBPROTEGE_ADMIN_PASSWORD}\n${WEBPROTEGE_ADMIN_PASSWORD}" | java -jar /usr/local/bin/webprotege-cli.jar create-admin-account
        touch /srv/webprotege/.admin-account-created
    else
        echo "WEBPROTEGE_ADMIN_USER and WEBPROTEGE_ADMIN_PASSWORD environment variables not set."
        echo "You will need to create an admin account manually after startup."
    fi
    
    # Stop Tomcat to restart it in foreground later
    catalina.sh stop
    sleep 5
fi

# Update mail settings if environment variables are provided
if [ -n "$MAIL_SMTP_HOST" ]; then
    sed -i "s/mail.smtp.host=.*/mail.smtp.host=$MAIL_SMTP_HOST/" /etc/webprotege/mail.properties
fi

if [ -n "$MAIL_SMTP_PORT" ]; then
    sed -i "s/mail.smtp.port=.*/mail.smtp.port=$MAIL_SMTP_PORT/" /etc/webprotege/mail.properties
fi

if [ -n "$MAIL_SMTP_FROM" ]; then
    sed -i "s/mail.smtp.from=.*/mail.smtp.from=$MAIL_SMTP_FROM/" /etc/webprotege/mail.properties
fi

if [ -n "$MAIL_SMTP_USER" ]; then
    sed -i "s/mail.smtp.user=.*/mail.smtp.user=$MAIL_SMTP_USER/" /etc/webprotege/mail.properties
fi

if [ -n "$MAIL_SMTP_PASSWORD" ]; then
    sed -i "s/mail.smtp.password=.*/mail.smtp.password=$MAIL_SMTP_PASSWORD/" /etc/webprotege/mail.properties
    sed -i "s/mail.smtp.auth=.*/mail.smtp.auth=true/" /etc/webprotege/mail.properties
fi

# Execute CMD
echo "Starting Tomcat..."
exec "$@"