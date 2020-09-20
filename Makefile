all:


bump-upload:
	$(MAKE) bump
	$(MAKE) upload

bump:
	bumpversion patch
	git push --tags
	git push

upload:
	rm -f dist/*
	rm -rf src/*.egg-info
	python setup.py sdist
	twine upload dist/*

test:
	$(MAKE) tests-clean tests

tests-clean:
	rm -rf out-comptests

tests:
	comptests --nonose duckietown_challenges_tests
