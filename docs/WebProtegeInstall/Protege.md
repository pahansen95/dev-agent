This page describes how to install WebProtégé 4.0.0.  Please note that these instructions are for system administrators/managers that want to configure a local installation of WebProtégé.  We prefer that you use the Stanford hosted version of WebProtégé at http://webprotege.stanford.edu, however, we realize that this is not possible in all cases and so we make WebProtégé available for local installations.  The instructions that follow assume familiarity with basic system admin tasks such as creating directories, setting file permissions etc.

# Contents

   * [Prerequisites](WebProtégé-4.0.0-Installation#prerequisites)
   * [Installation Instructions](WebProtégé-4.0.0-Installation#installation-instructions)
      * [Set up the necessary directories for WebProtégé](WebProtégé-4.0.0-Installation#set-up-the-necessary-directories-for-webprotégé)
         * [Create the WebProtégé data directory](WebProtégé-4.0.0-Installation#create-the-webprotégé-data-directory)
         * [Create the WebProtégé config directory](WebProtégé-4.0.0-Installation#create-the-webprotégé-config-directory)
         * [Create the WebProtégé logs directory](WebProtégé-4.0.0-Installation#create-the-webprotégé-logs-directory)
      * [Install and Setup WebProtégé](WebProtégé-4.0.0-Installation#install-and-setup-webprotégé)
         * [Install the WebProtégé WebApp](WebProtégé-4.0.0-Installation#install-the-webprotégé-webapp)
         * [Bootstrap WebProtégé with an Admin Account](WebProtégé-4.0.0-Installation#bootstrap-webprotégé-with-an-admin-account)
         * [Edit the WebProtégé Settings](WebProtégé-4.0.0-Installation#edit-the-webprotégé-settings)

# Prerequisites

WebProtégé is a Java WebApp. The following software components need to be installed to run WebProtégé:

- [Java 11](https://jdk.java.net/11/).
- [Tomcat](https://tomcat.apache.org), or some other servlet container.  In the setup instructions that follow, we refer to "Tomcat" as the servlet container.  We require Tomcat 7, 8 or 9. Tomcat 10 is not supported as Servlet 6.0 introduced many changes in package naming. 
- [MongoDB](https://docs.mongodb.com/manual/installation/). 

You can find installation and setup instructions for these components at their respective websites by following the links above.  You need to make sure that the MongoDB database server is running prior to performing the setup below.

**Important:** You should make sure that your servlet container is running in a JVM with the file encoding set to UTF-8. The recommended way to do this in Tomcat is to edit setenv.sh (or setenv.bat) from your CATALINA_INSTALLATION_DIR/bin, and add the line:
 ```export CATALINA_OPTS="$CATALINA_OPTS -Dfile.encoding=UTF-8"```. Alternatively, this can be specified as a command line argument when starting the servlet container i.e. ```-Dfile.encoding=UTF-8```.

# Installation Instructions

## Set up the necessary directories for WebProtégé

### Create the WebProtégé data directory

WebProtégé requires a directory, that we call the _data directory_ to store its data in.  This data directory _must_ exist prior to starting WebProtégé.  You can create the data directory anywhere on your system that is readable/writeable by Tomcat.  By default, WebProtégé expects the data directory to be ```/srv/webprotege```.  It is important that the data directory has the appropriate permissions so that Tomcat can _read_ from it and _write_ to it.

1. Create the data directory on your system.  We recommend you use the standard location, ```/srv/webprotege```.  On a Windows system this corresponds to ```C:\srv\webprotege```.
2. Ensure that the data directory that you've created has the appropriate permissions so that Tomcat can read from the directory and write to the directory.

_**Important:** If you have an existing WebProtégé 2.x installation *you will need to migrate the data that is stored by WebProtégé to the new backend format*.  To do this you should follow the [WebProtégé 2.x migration instructions](https://github.com/protegeproject/webprotege/wiki/WebProtégé-2.x-migration) before going any futher._

### Create the WebProtégé config directory

WebProtégé has two configuration files:

- **webprotege.properties**.  This file contains critical settings such as the path to the data directory and database connection information.
- **mail.properties**.  This file contains mail server settings that WebProtégé will use for sending out email notifications to users.

By default, both of these configuration files are embedded in the WebProtégé war file (in the ```WEB-INF/classes``` directory) and will be read from there.  However, we _strongly_ recommend that you make copies of these files and adjust the various configuration properties as necessary for your installation.  To do this, follow the steps below:

1. Create the directory to hold the WebProtégé configuration files.  On Linux/Unix/MacOS this should be ```/etc/webprotege```.  On Windows this should be ```C:\ProgramData\WebProtege``` (note that the ```ProgramData``` directory is a hidden directory).
2. Ensure that this directory has the appropriate permissions so that it can be _read_ by Tomcat.
3. Create a copy of the [```webprotege.properties```](https://github.com/protegeproject/webprotege/blob/master/webprotege-server-core/src/main/resources/webprotege.properties) file inside this configuration directory.
4. In the ```webprotege.properties``` file you should adjust the various properties as appropriate for your installation.  In particular, you should ensure that the ```data.directory``` property is set to point to the WebProtégé data directory for your installation. For example, on Linux/Unix/MacOS,

    ```properties
    data.directory=/srv/webprotege
    ```

    or on Windows,

    ```properties
    data.directory=C:\\srv\\webprotege
    ```

    Note that the default value for the data directory property is ```/srv/webprotege``` on Linux/Unix/MacOS and ```C:\srv\webprotege``` on Windows.  If you created the data directory in this location then you do not need to change this property.
4. Ensure that the ```webprotege.properties``` file can be _read_ by Tomcat.
5. Create a copy of the [```mail.properties```](https://github.com/protegeproject/webprotege/blob/master/webprotege-server-core/src/main/resources/mail.properties) file inside the configuration directory that you created.  You can copy the contents of the default [mail.properties](https://github.com/protegeproject/webprotege/blob/master/webprotege-server-core/src/main/resources/mail.properties) file and modify the various properties as appropriate for your installation.  The ```mail.properties``` file supports the standard [SMTP email configuration properties](https://javaee.github.io/javamail/docs/api/com/sun/mail/smtp/package-summary.html) used by Java.
6. Ensure that the ```mail.properties``` file can be _read_ Tomcat.

### Create the WebProtégé logs directory

WebProtégé writes various information to various log files when it is running.  The default location for these log files is the directory ```/var/log/webprotege``` on Linux/Unix/MacOS and ```C:\ProgramData\WebProtege\Logs``` on Windows.  You should therefore create the appropriate directory for your platform and ensure that Tomcat can write to it.

1. Create the directory ```/var/log/webprotege``` if you are using Linux/Unix/MacOS or ```C:\ProgramData\WebProtege\Logs``` if you are using Windows.
2. Ensure that the logs directory has the appropriate permissions so that Tomcat can _write_ to it.

## Install and Setup WebProtégé

### Install the WebProtégé WebApp

1.  **Make sure that Tomcat is stopped**.
2.  Remove any previous WebProtégé installations: In the Tomcat ```webapps``` directory, delete any existing ```webprotege.war``` file and any existing ```webprotege``` directory.
3. Download the WebProtégé 4.0.0 war file.
4. Rename the downloaded war file to ```webprotege.war```
5. Copy the ```webprotege.war``` file to the tomcat ```webapps``` directory.  You must ensure that the ```webprotege.war``` file has the appropriate permissions so that it can be _read_ by Tomcat.  _**Important:** You MUST not have more than one version of WebProtégé installed in the ```webapps``` directory._
6. Start Tomcat.
7. Ensure that WebProtégé is running by opening a Web browser and navigating to the WebProtégé home page.  If your server is accessed at ```https://my.server.address``` and Tomcat is running on port 8080, then the WebProtégé home page will be located at ```https://my.server.address:8080/webprotege```.  If there are any problems with missing directories or file permissions then an error page will be displayed.  Otherwise the login page for WebProtégé will be displayed.

### Bootstrap WebProtégé with an Admin Account

1. Download the [WebProtégé Command Line Tool](https://github.com/protegeproject/webprotege/releases/download/v4.0.0/webprotege-cli-4.0.0.jar).
2. In a terminal, set the working directory to the location of the ```webprotege-cli.jar``` file that you just downloaded. For example, use ```cd YOUR_WEBPROTEGE_CLI_DOWNLOAD_FOLDER``` in a terminal. 
3. Enter the following command into the terminal:

    ```bash
    java -jar webprotege-cli.jar create-admin-account
    ```
_Note: In the above command, replace ```webprotege_cli.jar``` with the one that you downloaded that may contain the version number, e.g., ```webprotege-4.0.0-beta-1-cli.jar```_

4. Follow the setup tool instructions in the terminal.  You will be asked to provide a user name and password for the admin account.  **You need this user name and password later on, so remember these details!**

### Edit the WebProtégé Settings

1. Open a web browser and enter the URL for the WebProtégé home page into the browser.  For example, assuming that your server is accessed at ```https://my.server.address``` and Tomcat is running on port ```8080```, the URL of the WebProtégé home page is:

    ```url
    https://my.server.address:8080/webprotege
    ```

2. Sign in using the admin account that you created as part of the setup above.
3. Once you have signed in, navigate to the application settings page at the URL obtained by appending ```#application/settings``` to the URL of the WebProtégé home page.  For example,

    ```url
    https://my.server.address:8080/webprotege#application/settings
    ```
4. On the **Main Settings** tab, specify an email address where critical system notifications can be sent to in the _System notification email address_ field.
5. On the **Main Settings** tab, specify the various URL components of the URL that is used to access your WebProtégé installation.  These details are used to compose user facing URLs in email notifications that WebProtégé sends out to users.  **The URL components should therefore reflect the public URL of your WebProtégé installation**.
    1. Specify the scheme users use to access your WebProtégé installation (either ```http``` or ```https```).
    2. Specify the host name that users use to access your WebProtégé installation (e.g. ```my.server.address```)
    3. Specify the port that users use to access your WebProtégé installation (e.g. 8080).  Note that the port number is optional.
    4. Specify the path that users use to access WebProtégé (e.g. /webprotege).  Note that the path is optional.
6. On the **Global Permissions** tab,
    1. Specify whether you want account creation enabled.
    2. Specify whether you want project creation enabled.
    3. Specify whether you want project upload enabled and optionally specify a max file size.
    4. Specify whether you want email notifications enabled.
7. Press the _Apply_ button to save the settings.