FROM ubuntu:18.04

RUN apt-get update \
    && apt-get install -y \
	curl \
	git \
	docker.io \
	python-pip \
	python-psutil \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose

WORKDIR /project

COPY . .

ARG REFRESHED_REQS=5

RUN pip install -r /project/requirements.txt && python setup.py install

ENTRYPOINT ["/usr/local/bin/dt-challenges-evaluator"]
