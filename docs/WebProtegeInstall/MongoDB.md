⸻

MongoDB 8.0 Community Edition (Debian .tgz Install) – Sysadmin Checklist

⸻

Preparation
	1.	Install Required Packages

sudo apt-get install libcurl4 libgssapi-krb5-2 libldap-common libwrap0 libsasl2-2 libsasl2-modules libsasl2-modules-gssapi-mit openssl liblzma5


	2.	Create Required Directories

sudo mkdir -p /var/lib/mongo
sudo mkdir -p /var/log/mongodb


	3.	Set Directory Ownership
Ensure the MongoDB user (or desired user) owns the above directories:

sudo chown $(whoami) /var/lib/mongo
sudo chown $(whoami) /var/log/mongodb



⸻

Installation
	4.	Download MongoDB Tarball
	•	Go to: MongoDB Download Center
	•	Select:
	•	Version: MongoDB 8.0
	•	Platform: Debian 64-bit (x86_64)
	•	Package: .tgz
	•	Download the file.
	5.	Extract Tarball

tar -zxvf mongodb-linux-*-8.0.x.tgz


	6.	Deploy Binaries
	•	Option A: Copy binaries into PATH

sudo cp /path/to/mongodb-directory/bin/* /usr/local/bin/


	•	Option B: Symlink binaries into PATH

sudo ln -s /path/to/mongodb-directory/bin/* /usr/local/bin/


	7.	Install MongoDB Shell (mongosh)
	•	Download mongosh separately from MongoDB Download Center.
	•	Extract and install it similarly.

⸻

Configuration
	8.	ulimit Adjustment (Recommended)
	•	Ensure nofile (open files) limit is ≥ 64000.
	•	Review /etc/security/limits.conf and /etc/systemd/system.conf if necessary.
	9.	Default Directory Expectations
	•	Data: /var/lib/mongo
	•	Logs: /var/log/mongodb
	•	Adjust paths if needed via mongod options or a mongod.conf file.
	10.	Bind IP for Network Access (Optional)
	•	By default, MongoDB binds to 127.0.0.1 (localhost only).
	•	To expose MongoDB externally:
	•	Update --bind_ip option or mongod.conf.
	•	Important: Secure the instance before exposing.

⸻

Startup & Verification
	11.	Start MongoDB Daemon

mongod --dbpath /var/lib/mongo --logpath /var/log/mongodb/mongod.log --fork


	12.	Verify Startup
	•	Check /var/log/mongodb/mongod.log for:

[initandlisten] waiting for connections on port 27017


	•	Warnings may appear but can often be ignored during initial setup.

	13.	Connect to MongoDB

mongosh



⸻

Notes
	•	Alternative: MongoDB recommends using apt for easier installation and upgrades if possible.
	•	Production Hardening: Review MongoDB’s Production Notes for best practices on performance, security, and configuration.

⸻