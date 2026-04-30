# vouch

## 🥁 Preparation

1. Install Docker Desktop - <https://www.docker.com/products/docker-desktop>

2. clone this repo & cd into the root of the repo where you can see docker-compose.yml

3. looking at the `.env.example` create a `.env` file in the repo.

4. setup git config just for this repo <https://support.atlassian.com/bitbucket-cloud/docs/configure-your-dvcs-username-for-commits/>

5. Install GPG Keychain and setup passwords - <https://gpgtools.org>

6. Make sure the commits are signed - <https://dev.to/devmount/signed-git-commits-in-vs-code-36do>

7. Make sure you edit the .git/config file with the following settings

```yaml
[user]
    name = <FULL NAME>
    email = <EMAIL>
    signingkey = <GPG KEY - LAST 16 DIGITS>
```

## 🪚 Setup

```bash
# First: To build and run the project
----------------------------------------------------------
# Make sure you are in the root of the repo where you can see docker-compose.yml
# Make sure you have created a .env file in the root of the repo
$ cp .env.example .env
# Build the project
$ docker compose build --no-cache backend
# Setup UV dependencies
$ docker compose up backend
# once the server is up and running (you can see the logs in the terminal), then kill it via keyboard shortcut
$ [CTRL + C]
# Run the following command to fully build and run the project
$ docker compose up
# (Optional IDE support) If you want imports to run correctly in your IDE, you can run the following command
$ cd src && uv sync --frozen --dev

# Second: Open a new tab and Load initial data
----------------------------------------------------------
# for the first time make sure you run the following command to migrate the database
$ docker exec -it vouch-backend-1 python manage.py migrate 
# (Optional) if there are any fixtures
$ docker exec -it vouch-backend-1 python manage.py loaddata vouch/fixtures/allauth.json
# Optional: Create super user (use it if needed)
$ docker exec -it vouch-backend-1 python manage.py createsuperuser

# Once the servers are up and running you can access the following:
Server should be running at http://127.0.0.1:8000
Celery Monitoring at http://127.0.0.1:8765
Kanchi - Celery Monitoring UI at http://127.0.0.1:3000
MailCatcher to catch local emails at http://127.0.0.1:1080
Ngrok Webhook at http://127.0.0.1:4040 - if this is required for this project
```

### 🐳 Makefile

```bash
# This project contains a Makefile featuring shortcuts to common commands run inside docker containers.
==========
$ make                                                        # -- Lists make commands
```

## 🐳 Docker Ops Cheatsheet

```bash
Docker
==========
$ docker compose up                                               # -- Compose the docker with logs
$ docker compose up -d                                            # -- Compose the docker without logs
$ docker compose logs                                             # -- Show logs from docker compose
$ docker compose down                                             # -- Stop all containers started via docker compose
$ docker container ls                                             # -- Show only list of running containers
$ docker ps                                                       # -- Show only list of running containers
$ docker ps -a                                                    # -- List of running containers in your system
$ docker ps -a -q                                                 # -- Show only list of running containers just their IDs
$ docker stop <CONTAINER ID>                                      # -- Stop containers (can pass mutiple IDs with space)
$ docker stop $(docker ps -a -q)                                  # -- Stop all containers
$ docker rm <CONTAINER ID>                                        # -- Remove containers with IDs
$ docker rm $(docker ps -a -q)                                    # -- Remove all containers
$ docker rm $(docker ps -aq)                                      # -- Remove all containers
$ docker exec -it <CONTAINER ID/NAME> sh                          # -- SSH into the docker container
$ docker image ls                                                 # -- List of docker images in your system
$ docker image ls -q                                              # -- List of docker images in your system just their IDs
$ docker image rm -f <IMAGE ID/NAME>                              # -- Remove image by force
$ docker rmi $(docker images -q)                                  # -- Remove all images
$ docker rmi $(docker images -q --filter "dangling=true")         # -- Remove all untagged images
$ docker volume ls                                                # -- List volumes
$ docker volume rm <VOLUME NAME>                                  # -- Remove one or more volumes
$ docker volume rm -f <VOLUME NAME>                               # -- Force remove one or more volumes
$ docker volume prune                                             # -- Remove all unused local volumes
$ docker volume inspect                                           # -- Display detailed information on one or more volumes

# Common commands:
$ docker exec -it vouch-backend-1 sh                            # -- SSH into the backend container
$ docker exec -it vouch-backend-1 zsh                           # -- (fancy) SSH via ZSH into the backend container
$ docker exec -it vouch-backend-1 startapp <APP NAME>           # -- Create a new app django app with a name
$ docker exec -it vouch-backend-1 shell                         # -- Django shell with iPython function
$ docker exec -it vouch-backend-1 uv tree --outdated --depth=1  # -- List outdated pip packages

# Shadcn Django commands
- <https://shadcn-django.com/accordion/>
$ shadcn_django list                                              # -- List all the components
$ addcomponent <component>                                        # -- Add a new component

# UV commands
$ uv sync                                                         # -- Sync with updating the uv.lock file
$ uv sync --locked                                                # -- (Dev only) Assert that the uv.lock will remain unchanged. 
$ uv sync --frozen                                                # -- Sync without updating the uv.lock file
$ uv tree                                                         # -- List installed pip packages
$ uv tree --group dev --outdated --depth=1                        # -- List outdated pip packages
$ uv add -U <package_name>                                        # -- Add a package
$ uv lock --upgrade                                               # -- Upgrade the uv.lock version of packages

# UV upgrade (Library upgrades -- tool I am still trying out)  https://github.com/Alirex/uv_upgrade
$ uv-upgrade --version                                            # -- Check the version of uv-upgrade
$ uv-upgrade                                                      # -- Show help for uv-upgrade

# pnpm commands
$ pnpm update                                                     # -- Update all packages
$ pnpm install <package_name>                                     # -- Install a package
$ pnpm remove <package_name>                                      # -- Remove a package

# If you have an error in the docker container and need to install a package:
$ docker run --name cont3 vouch-backend uv add <package_name>
$ docker run --name cont3 vouch-backend <command>

# Once you are in docker container:
$ startapp                                                        # -- Create a new app django app with a name
$ rmpyc                                                           # -- Clear all temporary python files
$ trans                                                           # -- Make messages for en_GB & de
$ compile                                                         # -- Compile messages for en_GB & de
$ shell                                                           # -- Django shell with iPython function

# If we need to rebuild just celery
$ docker compose up -d --no-deps --build celery-flower celery-beat celery-worker backend

# If we need to rebuild just backend
$ docker compose build --no-cache backend

PSQL
==========
$ docker exec -it vouch-db-1 bash                           # -- 1. SSH into docker-postgres image
$ su - postgres                                               # -- 2. switch user
$ psql -U vouch                                             # -- 3. run PSQL
$ \c postgres

if you are restoring a DB then you have to first stop the backend server via docker dashboard
make sure you add dump in the root folder and name it "backup.dump"
uncomment the volume line at the docker-compose.yml file under db service
delete the old DB by "DROP DATABASE vouch;"
create the same DB by "CREATE DATABASE vouch;"
leave the shell by "\q"
$ cd /docker-entrypoint-initdb.d/
$ psql -U vouch -d vouch -f backup.dump                   # -- 4. (optional) restore a DB

Change Passsword for Postgres
==========
$ docker exec -it vouch-db-1 psql -U vouch
$ ALTER USER vouch WITH PASSWORD 'new_password';

Updating Postgres version
==========
# BACKUP while running old version
$ docker exec -it vouch-db-1 pg_dumpall -U vouch > dump.sql
# Do the update in docker compose
$ docker stop vouch-db-1
$ docker rm vouch-db-1
$ docker volume rm vouch_postgres-data
$ docker compose down
$ docker compose up -d 
$ docker exec -i vouch-db-1 psql -U vouch < dump.sql

Terraform
==========
$ terraform init
$ terraform validate
$ terraform fmt
$ terraform fmt -check
$ terraform plan
$ terraform apply
$ terraform output -raw token_value
$ terraform destroy 
```

### ShadCN Commands (Outdated - check with Girish)

```bash
# Make sure you are in the /code/src/vouch directory
$ cd /code/src/vouch
# List all the components
$ shadcn_django list
# Add a new component
$ shadcn_django add <component> 
# Once the component is added, you can run the following command to apply the changes
$ mv /code/src/vouch/templates/cotton/<component> /code/src/vouch/templates/cotton/uikit/<component>
```

### Django UIKit Commands

**Important**: After moving components to the `uikit` folder, use them in templates with the `c-uikit.` prefix:

```django

<!-- ✅ Correct: Use c-uikit.component-name -->
<c-uikit.button variant="outline">Click Me</c-uikit.button>
<c-uikit.badge variant="secondary">Badge</c-uikit.badge>

<!-- ❌ Incorrect: Don't use c-component-name -->
<c-button variant="outline">Click Me</c-button>
```

### Tests

The tests are done automatically via github actions under this link - . However if you like to run tests manually follow the comands below

```bash
ssh into docker 
$ ruff check
$ basedpyright
$ coverage run manage.py test
$ coverage report --skip-covered --show-missing --omit="*/venv/*"
```

## 💫 Spec-Driven Development

This project uses [Spec-Kit](https://github.com/github/spec-kit) for spec-driven development, a methodology that emphasizes creating detailed specifications and implementation plans before writing code. This ensures better planning, consistency, and quality throughout the development process.

### Overview

Spec-Driven Development follows a structured workflow:

1. **Specify** - Create detailed feature specifications
2. **Plan** - Generate implementation plans with technical context
3. **Tasks** - Break down plans into actionable, dependency-ordered tasks
4. **Analyze** - Validate consistency across artifacts
5. **Implement** - Execute the implementation plan systematically

#### Spec-Kit Commands

All commands are available in Cursor via the `/speckit.*` prefix. Here's a quick reference:

```bash
# Step 1: Create Feature Specification
/speckit.specify <feature description>
# Example: /speckit.specify Add user authentication with OAuth2 support
# Creates: specs/<number>-<feature-name>/spec.md
# - Generates a feature specification from natural language
# - Creates a new git branch for the feature
# - Sets up the feature directory structure

# Step 2: Generate Implementation Plan
/speckit.plan
# Creates: specs/<feature-name>/plan.md, research.md, data-model.md, contracts/
# - Generates technical implementation plan
# - Resolves technical unknowns through research
# - Creates data models and API contracts
# - Validates against project constitution

# Step 3: Generate Task Breakdown
/speckit.tasks
# Creates: specs/<feature-name>/tasks.md
# - Breaks down plan into actionable tasks
# - Orders tasks by dependencies
# - Marks parallel execution opportunities
# - Organizes by user story priorities

# Step 4: Analyze Consistency (Optional)
/speckit.analyze
# - Performs cross-artifact consistency analysis
# - Identifies duplications and ambiguities
# - Validates against constitution
# - Provides remediation suggestions

# Step 5: Implement
/speckit.implement
# - Executes tasks from tasks.md in correct order
# - Validates checklists before implementation
# - Follows TDD approach when specified
# - Provides progress updates

# Additional Commands
/speckit.checklist                    # Create quality checklists (UX, security, testing, etc.)
/speckit.clarify                      # Clarify ambiguous requirements in spec
/speckit.constitution                 # View or update project constitution
```

#### Typical Workflow

```bash
# 1. Start with a feature idea
/speckit.specify Create a task management system with drag-and-drop boards

# 2. Generate the implementation plan (after reviewing spec.md)
/speckit.plan

# 3. Review the plan and research documents, then generate tasks
/speckit.tasks

# 4. (Optional) Analyze for consistency before implementation
/speckit.analyze

# 5. Implement the feature
/speckit.implement
```

#### Project Structure

Spec-driven artifacts are stored in `.specify/`:

```text
.specify/
├── memory/
│   └── constitution.md          # Project constitution (core principles)
├── templates/                   # Spec-kit templates
├── scripts/                     # Helper scripts
└── specs/                       # Feature specifications
    └── <number>-<feature-name>/
        ├── spec.md              # Feature specification
        ├── plan.md              # Implementation plan
        ├── tasks.md             # Task breakdown
        ├── research.md          # Technical research findings
        ├── data-model.md        # Data model design
        ├── contracts/           # API contracts
        └── checklists/          # Quality checklists
```

#### Key Principles

- **Constitution-First**: All specifications must align with `.specify/memory/constitution.md`
- **Test-Driven**: Tests are written before implementation for complex logic
- **Incremental Delivery**: Features are broken into independently testable user stories
- **Quality Gates**: All code must pass linting, tests, and coverage thresholds

#### Resources

- [Spec-Kit GitHub Repository](https://github.com/github/spec-kit) - Official documentation and examples
- `.specify/memory/constitution.md` - Project-specific development principles
- `.cursor/commands/speckit.*.md` - Detailed command documentation

### Ref

- <https://1password.community/discussion/133105/error-connecting-to-agent-permission-denied-when-forwarding-1password-ssh-agent-to-docker>
- <https://github.com/nickjj/docker-django-example>
