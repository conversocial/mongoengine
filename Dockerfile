FROM    ubuntu:18.04
MAINTAINER  Conversocial Developers "developers@conversocial.com"

RUN export DEBIAN_FRONTEND=noninteractive && \
apt-get update && \
apt-get -y install \
 curl \
 mongodb-clients \
 python-dev \
 python-setuptools \
 python-pip \
 python3-pip && \
pip install virtualenv tox && \
virtualenv /venv && \
mkdir /mongoengine

WORKDIR /mongoengine
CMD ["/bin/bash", "-c", "while :; do echo 'Hit CTRL+C'; sleep 10; done"]
