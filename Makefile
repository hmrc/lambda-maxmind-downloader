SHELL := /usr/bin/env bash
DOCKER_OK := $(shell type -P docker)
POETRY_OK := $(shell type -P poetry)
OPENSSL_OK := $(shell type -P openssl)
PYTHON_OK := $(shell type -P python)
PYTHON_VERSION := $(shell python -V | cut -d' ' -f2)
PYTHON_REQUIRED := $(shell cat .python-version)
BUCKET_NAME := txm-integration-lambda-functions
LAMBDA_NAME := lambda-maxmind-downloader
LATEST_TAG := $(shell git tag --sort=v:refname \
	| grep -E "^v[0-9]+\.[0-9]+\.[0-9]+" | tail -1 )
TAG_MAJOR_NUMBER := $(shell echo $(LATEST_TAG) | cut -f 1 -d '.' )
TAG_RELEASE_NUMBER := $(shell echo $(LATEST_TAG) | cut -f 2 -d '.' )
TAG_PATCH_NUMBER := $(shell echo $(LATEST_TAG) | cut -f 3 -d '.' )
LAMBDA_VERSION := $(shell git tag --sort=v:refname \
	| grep -E "^v[0-9]+\.[0-9]+\.[0-9]+" | tail -1 )
LAMBDA_FILE := ${LAMBDA_NAME}.${LAMBDA_VERSION}.zip

default: help

help: ## The help text you're reading
	@grep --no-filename -E '^[a-zA-Z1-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
.PHONY: help

check_poetry: check_python
	@echo '********** Checking for poetry installation *********'
    ifeq ('$(POETRY_OK)','')
	    $(error package 'poetry' not found!)
    else
	    @echo Found poetry!
    endif

check_docker:
	@echo '********** Checking for docker installation *********'
    ifeq ('$(DOCKER_OK)','')
	    $(error package 'docker' not found!)
    else
	    @echo Found docker!
    endif

check_openssl:
	@echo '********** Checking for openssl installation *********'
    ifeq ('$(OPENSSL_OK)','')
	    $(error package 'openssl' not found!)
    else
	    @echo Found openssl!
    endif

check_python:
	@echo '*********** Checking for Python installation ***********'
    ifeq ('$(PYTHON_OK)','')
	    $(error python interpreter: 'python' not found!)
    else
	    @echo Found Python
    endif
	@echo '*********** Checking for Python version ***********'
    ifneq ('$(PYTHON_REQUIRED)','$(PYTHON_VERSION)')
	    $(error incorrect version of python found: '${PYTHON_VERSION}'. Expected '${PYTHON_REQUIRED}'!)
    else
	    @echo Found Python ${PYTHON_REQUIRED}
    endif

setup: check_poetry
	@echo '**************** Creating virtualenv *******************'
	export POETRY_VIRTUALENVS_IN_PROJECT=true && poetry run pip install --upgrade pip
	poetry install --no-root
	@echo '*************** Installation Complete ******************'

setup_git_hooks: check_poetry
	@echo '****** Setting up git hooks ******'
	poetry run pre-commit install

install: setup setup_git_hooks  ## Install a local development environment

typechecking: setup
	poetry run mypy ./maxmind.py

black: setup
	poetry run black ./maxmind.py tests/*.py

security_checks: setup
	poetry run safety check
	poetry run bandit -r ./maxmind.py --skip B303

test: setup typechecking  ## Run tests
	find . -type f -name '*.pyc' -delete
	export PYTHONPATH="${PYTHONPATH}:`pwd`" && poetry run pytest 

clean:  ## Delete virtualenv
	rm -rf ./.venv
	if [ -d output ]; then rm -rf .output; fi

package: setup check_openssl  ## Create Lambda .zip and hash file
	mkdir -p pip_lambda_packages
	poetry export -f requirements.txt > ./requirements.txt --without-hashes
	pip install -t pip_lambda_packages -r ./requirements.txt
	cp -r maxmind.py pip_lambda_packages
	find ./pip_lambda_packages -type f | xargs chmod 644
	find ./pip_lambda_packages -type d | xargs chmod 755
	cd pip_lambda_packages && zip -r ../${LAMBDA_FILE} .
	openssl dgst -sha256 -binary ${LAMBDA_FILE} | openssl enc -base64 > ${LAMBDA_FILE}.base64sha256
	rm -rf pip_lambda_packages
	rm -rf ./requirements.txt

publish: ## Upload Lambda package and hash to S3
	aws s3 cp ${LAMBDA_FILE} s3://${BUCKET_NAME}/${LAMBDA_NAME}/${LAMBDA_FILE} --acl=bucket-owner-full-control ;\
	aws s3 cp ${LAMBDA_FILE}.base64sha256 s3://${BUCKET_NAME}/${LAMBDA_NAME}/${LAMBDA_FILE}.base64sha256 --content-type text/plain --acl=bucket-owner-full-control ;\

push_tags:
	git push --tags

ci_docker_build: check_docker
	docker build --build-arg APP_USER_ID=`id -u` --build-arg APP_GROUP_ID=`id -g` -t python-build-env -f Dockerfile.jenkins .

ci_setup: check_docker
	docker run -v `pwd`:/src --workdir /src python-build-env make clean setup

ci_test: check_docker
	docker run -v `pwd`:/src --workdir /src python-build-env make test

ci_security_checks:
	docker run -v `pwd`:/src --workdir /src python-build-env make security_checks

ci_package: check_docker
	docker run -v `pwd`:/src --workdir /src python-build-env make package

ci_publish: publish

ci_push_tags: push_tags

ci_bumpversion:
	git tag "$(TAG_MAJOR_NUMBER).$(TAG_RELEASE_NUMBER).$$(( $(TAG_PATCH_NUMBER) + 1))"

ci: ci_docker_build ci_setup ci_test ci_security_checks ci_bumpversion ci_package ci_push_tags ci_publish

docker_sh: ## Get a terminal in a 'python-build-env' container
	@docker run --rm -v `pwd`:/src --workdir /src -it python-build-env bash
.PHONY: docker_sh
