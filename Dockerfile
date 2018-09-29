FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y git python-pip  docker.io  curl python-psutil
RUN curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose

RUN chmod +x /usr/local/bin/docker-compose

COPY requirements.txt /project/requirements.txt
ARG REFRESHED_REQS=5
RUN pip install -r /project/requirements.txt


COPY src /project/src
COPY setup.py /project/setup.py


RUN cd /project && python setup.py install

CMD dt-challenges-evaluator --continuous
