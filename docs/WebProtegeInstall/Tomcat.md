⸻

Apache Tomcat 9.0.104 – Sysadmin Setup Checklist

⸻

Windows Installation (GUI Installer)

Preparation
	1.	Ensure Java 8 or Later Installed
	•	Verify 64-bit Java if OS is 64-bit.
	•	Set JAVA_HOME if auto-detection fails.
	2.	Download the Tomcat Installer
	•	Tomcat 9 Download Page

Installation
	3.	Run the Installer
	•	Proceed through the wizard interface.
	4.	Configure Key Installer Options
	•	Service Installation: Always installed as a Windows Service.
	•	Auto-start on Boot: Enable if needed via installer checkbox.
	•	Set Java Location: Confirm or manually select JRE/JDK location.
	•	Optionally use a custom config file:
	•	Supply via /C=<config file>, alongside /S (silent) and /D=<install path>.
	•	Config file uses name=value pairs (example options: JavaHome, TomcatPortHttp, TomcatAdminUsername, etc.).
	5.	Post-Install
	•	Shortcuts to Start/Stop and Configure Tomcat will be created.
	•	Note: No tray icon for service mode; icon appears only if manually started after install.

Additional References
	•	Tomcat Windows Service How-To

⸻

Unix/Linux Installation (Manual with jsvc)

Preparation
	1.	Install Required Tools
	•	C ANSI Compiler (e.g., GCC)
	•	GNU Autoconf
	•	Java Development Kit (JDK) 8 or later
	•	GNU Make (use gmake on BSD systems)
	2.	Set Environment

export JAVA_HOME=/path/to/jdk
export CATALINA_HOME=/path/to/tomcat



Installation
	3.	Build commons-daemon (jsvc)

cd $CATALINA_HOME/bin
tar xvfz commons-daemon-native.tar.gz
cd commons-daemon-*-native-src/unix
./configure
make
cp jsvc ../..
cd ../..



Running Tomcat as a Daemon
	4.	Launch Using jsvc

CATALINA_BASE=$CATALINA_HOME
cd $CATALINA_HOME
./bin/jsvc \
    -classpath $CATALINA_HOME/bin/bootstrap.jar:$CATALINA_HOME/bin/tomcat-juli.jar \
    -outfile $CATALINA_BASE/logs/catalina.out \
    -errfile $CATALINA_BASE/logs/catalina.err \
    -Dcatalina.home=$CATALINA_HOME \
    -Dcatalina.base=$CATALINA_BASE \
    -Djava.util.logging.manager=org.apache.juli.ClassLoaderLogManager \
    -Djava.util.logging.config.file=$CATALINA_BASE/conf/logging.properties \
    org.apache.catalina.startup.Bootstrap


	5.	(For Java 9+) Add JVM Access Flags
	•	Add these additional jsvc flags:

--add-opens=java.base/java.lang=ALL-UNNAMED \
--add-opens=java.base/java.io=ALL-UNNAMED \
--add-opens=java.base/java.util=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent=ALL-UNNAMED \
--add-opens=java.rmi/sun.rmi.transport=ALL-UNNAMED


	6.	Optional: Specify Server JVM
	•	Add -jvm server if JVM defaults incorrectly.

Service Management
	7.	Create Boot-Time Service
	•	Use $CATALINA_HOME/bin/daemon.sh as a template for a service under /etc/init.d/.
	•	Modify accordingly for your init system (SysV, systemd, etc.).
	8.	Run jsvc with Drop-Privileges (Optional)
	•	To improve security, start as root, then drop to a restricted user:

./bin/jsvc -user tomcat_user ...


	•	Remember to disable SecurityListener checks if doing so.

Debugging
	•	Run jsvc --help for full options.
	•	Use -debug to troubleshoot launch issues.

⸻

Notes
	•	Commons Daemon JAR must be in the runtime classpath (normally handled via bootstrap.jar manifest).
	•	Refer to the RUNNING.txt file bundled with Tomcat for extended guidance.