all:


bump-upload:
	$(MAKE) bump
	$(MAKE) upload

bump:
	bumpversion patch

upload:
	git push --tags
	git push
	rm -f dist/*
	rm -f src/*.egg-info
	python setup.py sdist
	twine upload dist/*
#
#
#branch=$(shell git rev-parse --abbrev-ref HEAD)
#
#name=duckietown/dt-challenges-evaluator:$(branch)
#name_rpi=duckietown/rpi-dt-challenges-evaluator:$(branch)
#
#build:
#	docker build --pull  -t $(name) .
#
#build-no-cache:
#	docker build --pull  --no-cache -t $(name) .
#
#push:
#	docker push $(name)

#
#
#build-arm:
#	docker build --pull -t $(name_rpi) -f Dockerfile.arm .
#
#build-arm-no-cache:
#	docker build --pull -t $(name_rpi) -f Dockerfile.arm --no-cache  .
#
#push-arm:
#	docker push $(name_rpi)



tests-clean:
	rm -rf out-comptests

tests:
	comptests --nonose duckietown_challenges_tests
