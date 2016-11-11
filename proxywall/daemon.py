#!/usr/bin/env python

import argparse
import os
import sys
import urlparse

from proxywall import constants
from proxywall import loggers
from proxywall import monitors
from proxywall.backend import *
from proxywall.commons import *
from proxywall.version import current_version

__BACKEND_TYPES = {"etcd": EtcdBackend}

_logger = loggers.getlogger('p.Daemon')


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-daemon', description=current_version.desc)

    parser.add_argument('-backend', dest='backend', default=os.getenv(constants.BACKEND_ENV),
                        help='which backend to use.')
    parser.add_argument('-networks', dest='networks', default=os.getenv(constants.NETWORKS_ENV),
                        help='interested container networks.')

    parser.add_argument('-template-src', dest='template_src', default=os.getenv(constants.TEMPLATE_SRC_ENV),
                        help='jinja2 src template file location.')
    parser.add_argument('-template-dest', dest='template_dest', default=os.getenv(constants.TEMPLATE_DEST_ENV),
                        help='out template file location.')

    parser.add_argument('-prev-cmd', dest='prev_cmd', default=os.getenv(constants.PREV_CMD_ENV),
                        help='command to run before generate template.')
    parser.add_argument('-post-cmd', dest='post_cmd', default=os.getenv(constants.POST_CMD_ENV),
                        help='command to run after generate template.')

    return parser.parse_args()


def main():
    callargs = _get_callargs()

    if not callargs.template_src:
        _logger.e('%s env not set, use -template-src instead, program exit.', constants.TEMPLATE_SRC_ENV)
        sys.exit(1)

    if not os.path.isfile(callargs.template_src):
        _logger.e('%s is not a file, daemon exit.', callargs.template_src)
        sys.exit(1)

    if not callargs.template_dest:
        _logger.e('%s env not set, use -template-dest instead, program exit.', constants.TEMPLATE_DEST_ENV)
        sys.exit(1)

    if not callargs.post_cmd:
        _logger.e('%s env not set, use -post-cmd instead, program exit.', constants.POST_CMD_ENV)
        sys.exit(1)

    networks = callargs.networks | split('[,;\s]') if callargs.networks else callargs.networks
    if not networks:
        _logger.e('%s env not set, use -networks instead, program exit.', constants.NETWORKS_ENV)
        sys.exit(1)

    backend_url = callargs.backend
    if not backend_url:
        _logger.e('%s env not set, use -backend instead, program exit.', constants.BACKEND_ENV)
        sys.exit(1)

    backend_type = urlparse.urlparse(backend_url).scheme | lowcase
    backend_cls = __BACKEND_TYPES.get(backend_type)
    if not backend_cls:
        _logger.e('backend[type=%s] not found, program exit.', backend_type)
        sys.exit(1)

    backend = backend_cls(backend_url, networks=networks)
    monitors.loop(backend,
                  prev_cmd=callargs.prev_cmd,
                  post_cmd=callargs.post_cmd,
                  template_src=callargs.template_src,
                  template_dest=callargs.template_dest)


if __name__ == '__main__':
    raise SystemExit(main())
