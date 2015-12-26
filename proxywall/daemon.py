#!/usr/bin/env python

import argparse
import os
import sys
import urlparse

from proxywall import loggers
from proxywall import monitors
from proxywall.backend import *
from proxywall.version import current_version

__BACKENDS = {"etcd": EtcdBackend}

_logger = loggers.get_logger('d.Daemon')


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-daemon', description=current_version.desc)

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
    callargs = _get_callargs()

    if not os.path.exists(callargs.template_source):
        print('ERROR: template file {} not exists..'.format(callargs.template_source))
        sys.exit(1)

    backend_url = callargs.backend
    backend_scheme = urlparse.urlparse(backend_url).scheme

    backend_cls = __BACKENDS.get(backend_scheme)
    if not backend_cls:
        print('ERROR: backend[type={}] not found.'.format(backend_scheme))
        sys.exit(1)

    backend = backend_cls(backend_url)
    monitors.loop(backend=backend,
                  prev_command=callargs.prev_command,
                  post_command=callargs.post_command,
                  template_source=callargs.template_source,
                  template_destination=callargs.template_destination)


if __name__ == '__main__':
    raise SystemExit(main())
