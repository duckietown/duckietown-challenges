
DOCKER_REGISTRY ?= docker.io
PIP_INDEX_URL ?= https://pypi.org/simple/

all:


bump: # v2
	bumpversion patch
	git push --tags
	git push


upload:
	rm -f dist/*
	rm -rf src/*.egg-info
	python3 setup.py sdist
	twine upload --skip-existing --verbose dist/*


test:
	$(MAKE) tests-clean tests

tests-clean:
	rm -rf out-comptests

tests:
	comptests --nonose duckietown_challenges_tests
