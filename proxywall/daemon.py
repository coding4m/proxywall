#!/usr/bin/env python

import argparse
import os
import sys
import urlparse

from proxywall import loggers
from proxywall import monitors
from proxywall.backend import *
from proxywall.commons import *
from proxywall.version import current_version

__BACKENDS = {"etcd": EtcdBackend}

_logger = loggers.getlogger('p.Daemon')


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-daemon', description=current_version.desc)

    parser.add_argument('-backend', dest='backend', required=True,
                        help='which backend to use.')

    parser.add_argument('-networks', dest='networks', required=True,
                        help='interested container networks .')

    parser.add_argument('-template-source', dest='template_source', required=True,
                        help='jinja2 template file location.')
    parser.add_argument('-template-destination', dest='template_destination', required=True,
                        help='out template file location.')

    parser.add_argument('-prev-command', dest='prev_command',
                        help='command to run before generate template.')
    parser.add_argument('-post-command', dest='post_command', required=True,
                        help='command to run after generate template.')

    return parser.parse_args()


def main():
    callargs = _get_callargs()

    networks = callargs.networks | split('[,;\s]')
    if not networks:
        _logger.e('networks must not be empty., daemon exit.')
        sys.exit(1)

    if not os.path.exists(callargs.template_source):
        _logger.e('template file %s not exists, daemon exit.', callargs.template_source)
        sys.exit(1)

    backend_url = callargs.backend
    backend_scheme = urlparse.urlparse(backend_url).scheme

    backend_cls = __BACKENDS.get(backend_scheme)
    if not backend_cls:
        _logger.e('backend[type=%s] not found, daemon exit.', backend_scheme)
        sys.exit(1)

    backend = backend_cls(backend_url, networks=networks)
    monitors.loop(backend,
                  prev_command=callargs.prev_command,
                  post_command=callargs.post_command,
                  template_source=callargs.template_source,
                  template_destination=callargs.template_destination)


if __name__ == '__main__':
    raise SystemExit(main())
