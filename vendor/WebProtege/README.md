# Protege Web Server

## Protégé Overview

**Protégé** is a free, open-source ontology editor and framework developed by the Stanford Center for Biomedical Informatics Research. It enables users to construct, visualize, and manage ontologies—formal representations of knowledge domains—facilitating the development of intelligent systems and semantic web applications.

### Key Features

- **Ontology Editing**  
  Protégé supports the creation and editing of ontologies in various formats, including [OWL (Web Ontology Language)](https://protege.stanford.edu/?utm_source=chatgpt.com) and [RDF (Resource Description Framework)](https://protege.stanford.edu/?utm_source=chatgpt.com).

- **Reasoning Support**  
  It integrates with reasoners like HermiT and Pellet to perform logical reasoning over ontologies, allowing users to infer new knowledge and check for consistency.  
  ([Getting Started with Protégé 4](https://protegewiki.stanford.edu/wiki/Protege4GettingStarted?utm_source=chatgpt.com))

- **Extensibility**  
  Protégé's modular architecture permits the addition of plugins, enabling customization and extension of its core functionalities.  
  ([Reference Example](https://web.stanford.edu/group/rubinlab/pubs/Protege-RadiologyTerminology.pdf?utm_source=chatgpt.com))

- **Collaboration**  
  [WebProtégé](https://protege.stanford.edu/software.php?utm_source=chatgpt.com) offers collaborative features such as shared editing, commenting, and change tracking, supporting distributed ontology development.

### Use Cases and Community Support

Protégé is widely adopted across various domains, including biomedicine, e-commerce, and organizational modeling.  
Its active user community contributes to its development, provides support, and shares plugins and ontologies.  
([Community Site](https://protege.stanford.edu/?utm_source=chatgpt.com))

### Access and Resources

- [**Protégé Desktop Download**](https://protege.stanford.edu/)
- [**WebProtégé Access**](http://webprotege.stanford.edu)
- [**Documentation and Tutorials**](https://protegewiki.stanford.edu/wiki/Main_Page)

### Webserver Overview

Building on the strengths of Protégé, **WebProtégé** extends ontology editing into the browser, offering a collaborative, real-time environment for distributed teams. It supports OWL 2 and RDF standards, enables threaded discussions on entities, maintains detailed change tracking, and allows customizable layouts through modular portlets. Available as both a hosted service at [webprotege.stanford.edu](https://webprotege.stanford.edu) and for self-hosting via Docker or traditional deployments, WebProtégé provides a lightweight yet powerful platform for ontology development without the need for local installations, making it particularly suited for dynamic, multi-user projects across diverse domains.

## Development

The current usage for WebProtege is to serve as the backing Onotology for the Dev Agent. 

### Docker Image

Currently, the Docker image bundles WebProtege & all of its dependencies into one container for fast & simple development.

## Docker Setup

### Components

The WebProtege Docker setup includes:
- Java 11 (Eclipse Temurin JDK)
- MongoDB 5.0
- Apache Tomcat 9.0.73
- WebProtege 4.0.0

### Quick Start

The WebProtege setup uses a simple shell script to manage the Docker container. The script requires the `$WORK_CACHE` environment variable to be set to specify where data will be stored.

1. **Ensure WORK_CACHE is set:**
   ```bash
   export WORK_CACHE="/path/to/cache/directory"
   ```

2. **Start WebProtege:**
   ```bash
   bash webprotege.sh start
   ```

3. **Access WebProtege:**
   - Open a browser and navigate to http://localhost:8080/webprotege
   - Login with the default admin credentials:
     - Username: admin
     - Password: admin123

### Available Commands

The `webprotege.sh` script supports the following commands:

- **start**: Build (if needed) and start the WebProtege container
- **stop**: Stop the running WebProtege container
- **status**: Show the current status of the WebProtege container
- **logs**: Display logs from the WebProtege container
- **shell**: Open a shell inside the running container

Examples:
```bash
# Start WebProtege
bash webprotege.sh start

# Check status
bash webprotege.sh status

# View logs (add -f to follow)
bash webprotege.sh logs -f

# Open shell in container
bash webprotege.sh shell

# Stop WebProtege
bash webprotege.sh stop
```

### Data Storage

All data is stored in the `$WORK_CACHE/webprotege` directory with the following structure:
- `data/`: WebProtege ontology data
- `config/`: WebProtege configuration files
- `logs/`: WebProtege logs
- `mongodb/`: MongoDB database files

### Configuration

You can modify configuration by editing the files in the `$WORK_CACHE/webprotege/config` directory:

1. **webprotege.properties**:
   - Contains WebProtege and MongoDB connection settings

2. **mail.properties**:
   - Contains email notification settings

Changes to these files will take effect after restarting the container.

### Troubleshooting

If you encounter issues:
1. Check container status: `bash webprotege.sh status`
2. View logs: `bash webprotege.sh logs`
3. Access container shell: `bash webprotege.sh shell`
4. Ensure $WORK_CACHE is properly set and the directory is writeable
5. Verify Docker is running correctly

### Security Notes

For production use:
- Change default admin credentials
- Secure MongoDB with authentication
- Use HTTPS for WebProtege
- Configure proper firewall rules