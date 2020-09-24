all:


bump-upload:
	$(MAKE) bump
	$(MAKE) upload

bump: # v2
	bumpversion patch
	git push --tags
	git push


upload: # v2
	aido-check-not-dirty
	aido-check-tagged
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
