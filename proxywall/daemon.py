#!/usr/bin/env python

import argparse
import os
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
                        help='template file location.')
    parser.add_argument('-template-destination', dest='template_destination', required=True,
                        help='out template file location.')

    parser.add_argument('-prev-command', dest='prev_command',
                        help='command to run before generate template.')
    parser.add_argument('-post-command', dest='post_command', required=True,
                        help='command to run after generate template.')

    return parser.parse_args()


def main():
    daemon_args = _get_daemon_args()

    if not os.path.exists(daemon_args.template_source):
        raise ValueError('file {} not exists.'.format(daemon_args.template_source))

    backend_url = daemon_args.backend
    backend_scheme = urlparse.urlparse(backend_url).scheme

    backend_cls = __BACKENDS.get(backend_scheme)
    if not backend_cls:
        raise BackendNotFound("backend[type={}] not found.".format(backend_scheme))

    backend = backend_cls(backend_options=backend_url)
    monitors.loop(backend=backend,
                  prev_command=daemon_args.prev_command,
                  post_command=daemon_args.post_command,
                  template_source=daemon_args.template_source,
                  template_destination=daemon_args.template_destination)


if __name__ == '__main__':
    raise SystemExit(main())
