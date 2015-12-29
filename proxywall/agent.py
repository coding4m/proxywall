#!/usr/bin/env python

import argparse
import sys
import urlparse

from proxywall import events
from proxywall import loggers
from proxywall.backend import *
from proxywall.version import current_version

__BACKENDS = {"etcd": EtcdBackend}

_logger = loggers.getlogger('p.Agent')


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-agent', description=current_version.desc)

    parser.add_argument('-backend', dest='backend', required=True,
                        help='which backend to use.')

    parser.add_argument('-docker-url', dest='docker_url', default='unix:///var/run/docker.sock',
                        help='docker daemon addr, default is unix:///var/run/docker.sock.')

    parser.add_argument('--docker-tlsverify', dest='docker_tls_verify', default=False, action='store_true')
    parser.add_argument('--docker-tlsca', dest='docker_tls_ca')
    parser.add_argument('--docker-tlskey', dest='docker_tls_key')
    parser.add_argument('--docker-tlscert', dest='docker_tls_cert')
    return parser.parse_args()


def main():
    callargs = _get_callargs()
    backend_url = callargs.backend
    backend_scheme = urlparse.urlparse(backend_url).scheme

    backend_cls = __BACKENDS.get(backend_scheme)
    if not backend_cls:
        _logger.e('backend[type=%s] not found, agent exit.', backend_scheme)
        sys.exit(1)

    backend = backend_cls(backend_url)
    events.loop(backend,
                callargs.docker_url,
                docker_tls_verify=callargs.docker_tls_verify,
                docker_tls_ca=callargs.docker_tls_ca,
                docker_tls_key=callargs.docker_tls_key,
                docker_tls_cert=callargs.docker_tls_cert)


if __name__ == '__main__':
    raise SystemExit(main())
