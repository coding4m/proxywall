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

    parser.add_argument('-template-src', dest='template_src', required=True,
                        help='jinja2 template file location.')
    parser.add_argument('-template-dest', dest='template_dest', required=True,
                        help='out template file location.')

    parser.add_argument('-prev-cmd', dest='prev_cmd',
                        help='command to run before generate template.')
    parser.add_argument('-post-cmd', dest='post_cmd', required=True,
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
                  prev_cmd=callargs.prev_cmd,
                  post_cmd=callargs.post_cmd,
                  template_src=callargs.template_src,
                  template_dest=callargs.template_dest)


if __name__ == '__main__':
    raise SystemExit(main())
