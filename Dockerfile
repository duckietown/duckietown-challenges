ARG AIDO_REGISTRY

FROM  ${AIDO_REGISTRY}/ubuntu:20.04

ARG PIP_INDEX_URL
ENV PIP_INDEX_URL=${PIP_INDEX_URL}


RUN apt-get update \
    && apt-get install -y \
	curl \
	git \
	docker.io \
	python3 \
	python3-pip \
    && curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && apt-get remove -y curl \
    && rm -rf /var/lib/apt/lists/*

RUN usermod -G docker -a root

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONIOENCODING=utf8

WORKDIR /project

RUN pip3 install -U pip>=20.2
COPY requirements.* ./
RUN cat requirements.* > .requirements.txt
RUN  pip3 install --use-feature=2020-resolver -r .requirements.txt


COPY  . .

RUN echo PATH = $PATH

RUN python3 setup.py install

RUN python3 -c "import duckietown_challenges; print(duckietown_challenges.__file__)"
RUN dt-challenges-cli -h || true

RUN pip3 list
RUN pipdeptree

ENTRYPOINT ["dt-challenges-cli"]
