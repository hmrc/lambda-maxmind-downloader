SHELL := /usr/bin/env bash
ARTIFACT := maxmind-downloader.zip

MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
path := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))


.PHONY: test

install-pipenv:
	@echo "Installing pipenv"
	@pip install pipenv

test-dependencies:
	@pipenv install --dev

test: test-dependencies
	@pipenv run nosetests --nologcapture --with-coverage --cover-erase --cover-package maxmind

test-format: test-dependencies
	@pipenv run flake8 maxmind.py

test-safety: test-dependencies
	@pipenv check

test-all: test test-format test-safety

build: clean install-pipenv
	umask 0022; bin/build_artifact.sh $(path)/target/$(ARTIFACT)

push-s3:
	@aws s3 cp target/$(ARTIFACT) s3://$(S3_BUCKET)/$(ARTIFACT) --acl=bucket-owner-full-control
	@aws s3 cp target/$(ARTIFACT).base64sha256 s3://$(S3_BUCKET)/$(ARTIFACT).base64sha256 --acl=bucket-owner-full-control --content-type=text/plain

clean:
	@echo "Cleaning up folder"
	@rm -rf target || true 
	@pipenv --rm || true 
