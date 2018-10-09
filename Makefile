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
	python setup.py sdist
	twine upload dist/*


branch=$(shell git rev-parse --abbrev-ref HEAD)

name=duckietown/dt-challenges-evaluator:$(branch)
name_rpi=duckietown/rpi-dt-challenges-evaluator:$(branch)

build:
	docker build -t $(name) .

build-no-cache:
	docker build --no-cache -t $(name) .

push:
	docker push $(name)



build-rpi:
	docker build -t $(name_rpi) -f Dockerfile.rpi .

build-no-cache-rpi:
	docker build -t $(name_rpi) -f Dockerfile.rpi --no-cache  .

push-rpi:
	docker push $(name_rpi)



tests-clean:
	rm -rf out-comptests

tests:
	comptests --nonose duckietown_challenges_tests
