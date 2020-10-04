
AIDO_REGISTRY ?= docker.io
PIP_INDEX_URL ?= https://pypi.org/simple

all:


bump: # v2
	bumpversion patch
	git push --tags
	git push

upload: # v3
	aido-check-not-dirty
	aido-check-tagged
	aido-check-need-upload --package duckietown-challenges-daffy make upload-do

upload-do:
	rm -f dist/*
	rm -rf src/*.egg-info
	python setup.py sdist
	twine upload --skip-existing --verbose dist/*


test:
	$(MAKE) tests-clean tests

tests-clean:
	rm -rf out-comptests

tests:
	comptests --nonose duckietown_challenges_tests



repo0=$(shell basename -s .git `git config --get remote.origin.url`)
repo=$(shell echo $(repo0) | tr A-Z a-z)
branch=$(shell git rev-parse --abbrev-ref HEAD)
tag=$(AIDO_REGISTRY)/duckietown/$(repo):$(branch)


build_options = \
	--build-arg PIP_INDEX_URL=$(PIP_INDEX_URL) \
	--build-arg AIDO_REGISTRY=$(AIDO_REGISTRY) \
	$(shell aido-labels)


update-reqs:
	pur --index-url $(PIP_INDEX_URL) -r requirements.txt -f -m '*' -o requirements.resolved
	aido-update-reqs requirements.resolved

build: update-reqs
	docker build --pull -t $(tag)  $(build_options) .

build-no-cache: update-reqs
	docker build --pull -t $(tag)  $(build_options) --no-cache .

push:
	docker push $(tag)
