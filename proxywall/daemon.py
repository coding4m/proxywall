#!/usr/bin/env python

import argparse
import urlparse

from proxywall import loggers
from proxywall import monitors
from proxywall.backend import *
from proxywall.errors import *
from proxywall.version import current_version

__BACKENDS = {"etcd": EtcdBackend}

_logger = loggers.get_logger('d.Daemon')


def _get_daemon_args():
    parser = argparse.ArgumentParser(prog='dnswall-daemon', description=current_version.desc)

    parser.add_argument('-backend', dest='backend', required=True,
                        help='which backend to use.')

    parser.add_argument('-template-source', dest='template_source', required=True,
                        help='which backend to use.')
    parser.add_argument('-template-destination', dest='template_destination', required=True,
                        help='which backend to use.')
    parser.add_argument('-template-signal', dest='template_signal', required=True,
                        help='which backend to use.')

    return parser.parse_args()


def main():
    daemon_args = _get_daemon_args()

    backend_url = daemon_args.backend
    backend_scheme = urlparse.urlparse(backend_url).scheme

    backend_cls = __BACKENDS.get(backend_scheme)
    if not backend_cls:
        raise BackendNotFound("backend[type={}] not found.".format(backend_scheme))

    backend = backend_cls(backend_options=backend_url)
    monitors.loop(backend=backend,
                  template_signal=daemon_args.template_signal,
                  template_source=daemon_args.template_source,
                  template_destination=daemon_args.template_destination)


if __name__ == '__main__':
    raise SystemExit(main())
