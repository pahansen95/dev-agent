# Base image with Java 11 (required for WebProtege)
FROM eclipse-temurin:11-jdk

# Set environment variables
ENV CATALINA_HOME=/opt/tomcat
ENV PATH=$CATALINA_HOME/bin:$PATH
ENV JAVA_OPTS="-Dfile.encoding=UTF-8"
ENV MONGODB_DATA_DIR=/data/db
ENV WEBPROTEGE_DATA_DIR=/srv/webprotege
ENV WEBPROTEGE_CONFIG_DIR=/etc/webprotege
ENV WEBPROTEGE_LOGS_DIR=/var/log/webprotege

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    jq \
    libcurl4 \
    libgssapi-krb5-2 \
    libldap-common \
    libwrap0 \
    libsasl2-2 \
    libsasl2-modules \
    libsasl2-modules-gssapi-mit \
    openssl \
    liblzma5 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy versions.json to use for all component versions
COPY versions.json /opt/webprotege/versions.json

# Install MongoDB from tarball as per documentation
RUN export MONGODB_VERSION=$(jq -r '.mongodb' /opt/webprotege/versions.json) \
    && mkdir -p /tmp/mongodb \
    && cd /tmp/mongodb \
    && curl -sSfL "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-debian12-${MONGODB_VERSION}.tgz" -o mongodb.tgz \
    && tar -zxvf mongodb.tgz \
    && cd mongodb-linux-x86_64-debian12-${MONGODB_VERSION} \
    && cp bin/* /usr/local/bin/ \
    # Create required directories
    && mkdir -p ${MONGODB_DATA_DIR} \
    && mkdir -p /var/log/mongodb \
    && chown -R 2000:2000 ${MONGODB_DATA_DIR} /var/log/mongodb
    # No Cleanup; /tmp is a tmpfs mount

# Install MongoDB Shell (mongosh) separately as per documentation
RUN export MONGOSH_VERSION=$(jq -r '.mongosh' /opt/webprotege/versions.json) \
    && mkdir -p /tmp/mongosh \
    && cd /tmp/mongosh \
    && curl -sSfL "https://downloads.mongodb.com/compass/mongosh-${MONGOSH_VERSION}-linux-x64.tgz" -o mongosh.tgz \
    && tar -zxvf mongosh.tgz \
    && cp mongosh-${MONGOSH_VERSION}-linux-x64/bin/* /usr/local/bin/
    # No Cleanup; /tmp is a tmpfs mount

# Copy Tomcat configuration files
COPY setenv.sh /tmp/

# Install Tomcat
RUN export TOMCAT_VERSION=$(jq -r '.tomcat' /opt/webprotege/versions.json) \
    && mkdir -p ${CATALINA_HOME} \
    && curl -sSfL "https://archive.apache.org/dist/tomcat/tomcat-9/v${TOMCAT_VERSION}/bin/apache-tomcat-${TOMCAT_VERSION}.tar.gz" -o tomcat.tar.gz \
    && tar -xzf tomcat.tar.gz -C ${CATALINA_HOME} --strip-components=1 \
    && rm tomcat.tar.gz \
    && rm -rf ${CATALINA_HOME}/webapps/* \
    && mkdir -p ${CATALINA_HOME}/conf/Catalina/localhost \
    && mv /tmp/setenv.sh ${CATALINA_HOME}/bin/setenv.sh \
    && chmod +x ${CATALINA_HOME}/bin/setenv.sh

# Create required directories for WebProtege
RUN mkdir -p ${WEBPROTEGE_DATA_DIR} \
    && mkdir -p ${WEBPROTEGE_CONFIG_DIR} \
    && mkdir -p ${WEBPROTEGE_LOGS_DIR} \
    && mkdir -p /opt/webprotege

# Download WebProtégé WAR and CLI tool
RUN export WEBPROTEGE_VERSION=$(jq -r '.webprotege' /opt/webprotege/versions.json | sed 's/^v//') \
    && curl -sSfL "https://github.com/protegeproject/webprotege/releases/download/v${WEBPROTEGE_VERSION}/webprotege-server-${WEBPROTEGE_VERSION}.war" -o webprotege-server.war \
    && mv webprotege-server.war ${CATALINA_HOME}/webapps/webprotege-server.war \
    && curl -sSfL "https://github.com/protegeproject/webprotege/releases/download/v${WEBPROTEGE_VERSION}/webprotege-cli-${WEBPROTEGE_VERSION}.jar" -o webprotege-cli.jar \
    && mv webprotege-cli.jar /opt/webprotege/webprotege-cli.jar

# Copy configuration files to a backup location for entrypoint script to use
COPY webprotege.properties /opt/webprotege/default-webprotege.properties
COPY mail.properties /opt/webprotege/default-mail.properties

# Set permissions
RUN chmod -R 777 ${WEBPROTEGE_DATA_DIR} ${WEBPROTEGE_LOGS_DIR} ${WEBPROTEGE_CONFIG_DIR} ${CATALINA_HOME} /opt/webprotege

# Create non-root user with GID/UID 2000 to avoid conflicts
RUN groupadd -r webprotege -g 2000 && \
    useradd -r -g webprotege -u 2000 -d ${WEBPROTEGE_DATA_DIR} webprotege && \
    chown -R webprotege:webprotege ${WEBPROTEGE_DATA_DIR} ${WEBPROTEGE_LOGS_DIR} \
    ${WEBPROTEGE_CONFIG_DIR} ${CATALINA_HOME}/webapps /opt/webprotege

# Expose ports
# - 8080: Tomcat HTTP port
# - 27017: MongoDB port
EXPOSE 8080 27017

# Define volumes
VOLUME ["${WEBPROTEGE_DATA_DIR}", "${WEBPROTEGE_LOGS_DIR}", "${WEBPROTEGE_CONFIG_DIR}", "${MONGODB_DATA_DIR}"]

# Copy service management framework and scripts
COPY service.sh service-defs.sh /opt/webprotege/
COPY healthcheck.sh /usr/local/bin/
COPY entrypoint.sh /

# Make scripts executable
RUN chmod +x /usr/local/bin/healthcheck.sh /entrypoint.sh /opt/webprotege/service.sh /opt/webprotege/service-defs.sh

# Set entrypoint
ENTRYPOINT ["bash", "/entrypoint.sh"]

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 CMD ["/usr/local/bin/healthcheck.sh"]