ARG DOCKER_REGISTRY

FROM library/ubuntu:20.04

ARG PIP_INDEX_URL="https://pypi.org/simple"
ENV PIP_INDEX_URL=${PIP_INDEX_URL}


RUN apt-get update \
    && apt-get install -y \
	curl \
	git \
	docker.io \
	python3 \
	python3-pip \
    && curl -L https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && apt-get remove -y curl \
    && rm -rf /var/lib/apt/lists/*

RUN usermod -G docker -a root

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONIOENCODING=utf8

WORKDIR /project

COPY requirements.* ./
RUN cat requirements.* > .requirements.txt
RUN python3 -m pip install  -r .requirements.txt


COPY  . .

RUN echo PATH = $PATH

RUN python3 setup.py install

RUN python3 -c "import duckietown_challenges; print(duckietown_challenges.__file__)"
RUN dt-challenges-cli -h || true

RUN python3 -m pip list
RUN pipdeptree

ENTRYPOINT ["dt-challenges-cli"]
