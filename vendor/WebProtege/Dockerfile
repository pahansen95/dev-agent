FROM eclipse-temurin:11-jdk-jammy as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    maven \
    git \
    && rm -rf /var/lib/apt/lists/*

# Clone and build WebProtege
WORKDIR /build
RUN git clone https://github.com/protegeproject/webprotege.git
WORKDIR /build/webprotege
RUN mvn clean package -DskipTests

# Download CLI tool for admin account creation
RUN mkdir -p /build/cli
RUN wget -O /build/cli/webprotege-cli.jar https://github.com/protegeproject/webprotege/releases/download/v4.0.0/webprotege-cli-4.0.0.jar

# Final stage
FROM eclipse-temurin:11-jre-jammy

# Install MongoDB and Tomcat dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libcurl4 \
    libgssapi-krb5-2 \
    libldap-common \
    libwrap0 \
    libsasl2-2 \
    libsasl2-modules \
    libsasl2-modules-gssapi-mit \
    openssl \
    liblzma5 \
    && rm -rf /var/lib/apt/lists/*

# Install MongoDB
WORKDIR /tmp
RUN wget -qO - https://www.mongodb.org/static/pgp/server-8.0.asc | apt-key add - \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/8.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-8.0.list \
    && apt-get update \
    && apt-get install -y mongodb-org \
    && rm -rf /var/lib/apt/lists/*

# Install Tomcat
ENV CATALINA_HOME /usr/local/tomcat
ENV PATH $CATALINA_HOME/bin:$PATH

RUN mkdir -p "$CATALINA_HOME"
WORKDIR $CATALINA_HOME

ARG TOMCAT_VERSION=9.0.104
ARG TOMCAT_DOWNLOAD_URL=https://archive.apache.org/dist/tomcat/tomcat-9/v${TOMCAT_VERSION}/bin/apache-tomcat-${TOMCAT_VERSION}.tar.gz

RUN wget -O tomcat.tar.gz "$TOMCAT_DOWNLOAD_URL" \
    && tar -xf tomcat.tar.gz --strip-components=1 \
    && rm bin/*.bat \
    && rm tomcat.tar.gz*

# Create necessary directories for WebProtege
RUN mkdir -p /srv/webprotege \
    && mkdir -p /etc/webprotege \
    && mkdir -p /var/log/webprotege

# Copy WebProtege webapp from builder
COPY --from=builder /build/webprotege/webprotege-server/target/webprotege-server-*.war $CATALINA_HOME/webapps/webprotege.war

# Copy CLI tool for admin setup
COPY --from=builder /build/cli/webprotege-cli.jar /usr/local/bin/webprotege-cli.jar

# Create WebProtege configuration files
RUN echo "data.directory=/srv/webprotege" > /etc/webprotege/webprotege.properties
RUN cat > /etc/webprotege/mail.properties << 'EOF'
mail.smtp.auth=false
mail.smtp.user=user
mail.smtp.password=password
mail.smtp.host=localhost
mail.smtp.port=25
mail.transport.protocol=smtp
mail.smtp.from=webprotege@example.org
EOF

# Set proper permissions
RUN chmod -R 755 /srv/webprotege \
    && chmod -R 755 /var/log/webprotege \
    && chmod -R 755 /etc/webprotege

# Set Tomcat to use UTF-8 encoding
RUN echo 'export CATALINA_OPTS="$CATALINA_OPTS -Dfile.encoding=UTF-8"' > $CATALINA_HOME/bin/setenv.sh \
    && chmod +x $CATALINA_HOME/bin/setenv.sh

# Create startup script
WORKDIR /
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose ports
EXPOSE 8080
EXPOSE 27017

# Volumes for persistence
VOLUME ["/srv/webprotege", "/var/log/webprotege", "/etc/webprotege", "/data/db"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["catalina.sh", "run"]