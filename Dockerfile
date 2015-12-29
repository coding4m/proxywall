FROM python:2.7-slim
MAINTAINER coding4m@gmail.com

ADD . /var/proxywall/
RUN cd /var/proxywall/ && python setup.py install
ENTRYPOINT ["/usr/local/bin/proxywall-client"]
