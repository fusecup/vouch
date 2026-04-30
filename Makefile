# Determine docker compose client
UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	DOCKER_COMPOSE_CLIENT := docker compose
else
	# Assume OS is OSX
	DOCKER_COMPOSE_CLIENT := docker-compose
endif

# Put any command that doesn't create a file here (almost all of the commands)
.PHONY: \
	attach \
	ruff \
	ruff_check \
	help \
	manage \
	migrate \
	migrations \
	shell \
	up \
	zsh \

usage:
	@echo "Available commands:"
	@echo "attach..........................Attach to backend container. Useful for when using ipdb"
	@echo "ruff............................Runs python ruff and formats files."
	@echo "ruff_check......................Runs python ruff. Checks files only."
	@echo "help............................Display available commands"
	@echo "manage..........................Django's manage.py command"
	@echo "migrate........................ Runs Django's makemigrations command"
	@echo "migrations......................Runs Django's migrate command"
	@echo "shell...........................Django's shell plus command"
	@echo "up..............................Runs docker compose up command"
	@echo "zsh.............................Enter backend container using zsh"

PROJECT_DIR=vouch

attach:
	@docker attach ${PROJECT_DIR}-backend-1

ruff:
	@${DOCKER_COMPOSE_CLIENT} run --rm backend ruff check ${PROJECT_DIR} ${ARGS}

ruff_check:
	$(MAKE) ruff check ${ARGS}

help:
	$(MAKE) usage

manage:
	@${DOCKER_COMPOSE_CLIENT} run --rm ${OPTIONS} backend python3 ${PYTHON_ARGS} manage.py ${ARGS}

migrate:
	$(MAKE) manage ARGS="migrate ${ARGS}"

migrations:
	$(MAKE) manage ARGS="makemigrations ${ARGS}"

shell:
	$(MAKE) manage ARGS="shell ${ARGS}"

up:
	@${DOCKER_COMPOSE_CLIENT} up ${ARGS}

zsh:
	@${DOCKER_COMPOSE_CLIENT} run --rm backend zsh
