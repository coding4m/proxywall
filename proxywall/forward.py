import argparse
import os
import sys

from twisted.internet import reactor
from twisted.web import server
from twisted.web.proxy import ReverseProxyResource

from proxywall import constants
from proxywall import loggers
from proxywall.commons import *
from proxywall.version import current_version

__ADDRPAIR_LEN = 2
_logger = loggers.getlogger('p.Forward')


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-forward', description=current_version.desc)

    parser.add_argument('-forward-host', dest='forward_host',
                        default=os.getenv(constants.FORWARD_HOST))

    parser.add_argument('-forward-port', dest='forward_port', type=int,
                        default=os.getenv(constants.FORWARD_PORT, 80))

    parser.add_argument('-forward-path', dest='forward_path',
                        default=os.getenv(constants.FORWARD_PATH, ''))

    parser.add_argument('--addr', dest='addr',
                        default=os.getenv(constants.ADDR_ENV, '0.0.0.0:8888'))

    return parser.parse_args()


def main():
    callargs = _get_callargs()

    if not callargs.forward_host:
        _logger.e('%s env not set, use -forward-host instead, program exit.', constants.FORWARD_HOST)
        sys.exit(1)

    listen_addr = callargs.addr | split(':')
    if len(listen_addr) != __ADDRPAIR_LEN:
        _logger.e('addr must like 0.0.0.0:8888 format, program exit.')
        sys.exit(1)

    forward_host = callargs.forward_host
    forward_port = callargs.forward_port
    forward_path = callargs.forward_path

    forward_dispatcher = ReverseProxyResource(forward_host, forward_port, forward_path)
    listen_port, listen_host = listen_addr[1] | as_int, listen_addr[0]
    reactor.listenTCP(listen_port, server.Site(forward_dispatcher), interface=listen_host)

    _logger.w('waitting request on [tcp/%s].', callargs.addr)
    reactor.run()


if __name__ == '__main__':
    raise SystemExit(main())
