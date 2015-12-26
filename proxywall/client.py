#!/usr/bin/env python

import argparse
import json
import os
import sys
import traceback
import urlparse

from proxywall import loggers
from proxywall.backend import *
from proxywall.commons import *

__ADDRPAIR_LEN = 2
__BACKENDS = {"etcd": EtcdBackend}

_logger = loggers.get_logger('d.Client')


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-client',
                                     epilog='''Run 'proxywall-client COMMAND -h' for more information on a command.''',
                                     description='proxywall client for proxy operations.')

    parser.add_argument('-backend', dest='backend',
                        help='which backend to use. if not set, use BACKEND env instead.')

    subparsers = parser.add_subparsers(help='avaliables commands.')

    subparser_ls = subparsers.add_parser('ls', help='ls proxy.')
    subparser_ls.add_argument('name', nargs='?',
                              help='list proxy start with name. if not set, list all.')
    subparser_ls.set_defaults(action=_backend_ls)

    subparser_rm = subparsers.add_parser('rm', help='rm proxy use a json format file.')
    subparser_rm.add_argument('json', help='proxy json file.')
    subparser_rm.set_defaults(action=_backend_rm)

    subparser_add = subparsers.add_parser('add', help='add proxy use a json format file.')
    subparser_add.add_argument('json', help='proxy json file.')
    subparser_add.set_defaults(action=_backend_add)
    return parser.parse_args()


def main():
    callargs = _get_callargs()

    backend_url = callargs.backend if callargs.backend else os.getenv('BACKEND')
    if not backend_url:
        print('ERROR: BACKEND env not set, use -backend BACKEND instead.')
        sys.exit(1)

    backend_scheme = urlparse.urlparse(backend_url).scheme

    backend_cls = __BACKENDS.get(backend_scheme)
    if not backend_cls:
        print('ERROR: backend[type={}] not found.'.format(backend_scheme))
        sys.exit(1)

    backend = backend_cls(backend_url)
    callargs.action(backend, callargs)


def _backend_ls(backend, callargs):
    proxy_details = backend.lookall(name=callargs.name)
    dict_details = proxy_details | collect(lambda it: it.to_dict()) | as_list
    print json.dumps(dict_details, indent=4, sort_keys=True)


def _backend_rm(backend, callargs):
    try:
        proxy_detail = _parse_proxy_details(callargs)
        backend.unregister_all(proxy_detail.name, proxy_detail.nodes)
    except:
        traceback.print_exc()
    else:
        print('OK.')


def _parse_proxy_details(callargs):
    proxyjson = ''

    with open(callargs.json, 'r') as f:
        while True:
            proxydata = f.read(1024)
            if not proxydata:
                break
            proxyjson += proxydata

    proxylist = ProxyDetail.from_dict(json.loads(proxyjson))
    return proxylist


def _backend_add(backend, callargs):
    try:
        proxy_detail = _parse_proxy_details(callargs)
        backend.register_all(proxy_detail.name, proxy_detail.nodes)
    except:
        traceback.print_exc()
    else:
        print('OK.')


if __name__ == '__main__':
    raise SystemExit(main())
