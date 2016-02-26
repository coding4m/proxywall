import argparse
import os
import re
import sys

from twisted.internet import reactor
from twisted.python.compat import nativeString
from twisted.web import server, resource
from twisted.web.error import UnsupportedMethod

from proxywall import constants
from proxywall import loggers
from proxywall.commons import *
from proxywall.version import current_version

__ADDRPAIR_LEN = 2
_logger = loggers.getlogger('p.Redirect')


class IRedirectHandler(resource.Resource):
    """

    """

    def __init__(self):
        resource.Resource.__init__(self)

    def render(self, request):
        """

        :param request:
        :return:
        """
        m = getattr(self, 'render_' + nativeString(request.method.lower()), None)
        if not m:
            try:
                allowed_methods = self.allowed_methods
            except AttributeError:
                allowed_methods = resource._computeAllowedMethods(self)
            raise UnsupportedMethod(allowed_methods)
        return m(request)

    def render_head(self, request):
        return self.render_get(request)


class RedirectHandler(IRedirectHandler):
    """

    """

    def __init__(self, redirect_url):
        IRedirectHandler.__init__(self)
        self._redirect_url = redirect_url

    def render_get(self, request):
        """

        :param request:
        :return:
        """
        request.redirect(self._redirect_url)
        return ''


class RedirectDispatcher(IRedirectHandler):
    """

    """

    def __init__(self, default_redirect_url, redirect_rules):
        """

        :param default_redirect_url:
        :param redirect_rules:
        :return:
        """
        IRedirectHandler.__init__(self)
        self._default_redirect_url = default_redirect_url
        self._redirect_rules = redirect_rules \
                               | collect(lambda it: (it[0], it[1], len(it[0]))) \
                               | as_set \
                               | as_tuple \
                               | sort(cmp=lambda x, y: cmp(y[2], x[2])) \
                               | as_tuple

    def getChild(self, path, request):
        """

        :param path:
        :param request:
        :return:
        """
        redirect_rule = self._redirect_rules | select(lambda it: re.match(it[0], request.path)) | first
        return RedirectHandler(redirect_rule[1]) \
            if redirect_rule else RedirectHandler(self._default_redirect_url)


def _get_callargs():
    parser = argparse.ArgumentParser(prog='proxywall-redirect', description=current_version.desc)

    parser.add_argument('-default-redirect-url', dest='default_redirect_url',
                        default=os.getenv(constants.DEFAULT_REDIRECT_URL))

    parser.add_argument('-redirect-rules', dest='redirect_rules',
                        default=os.getenv(constants.REDIRECT_RULES, ''))

    parser.add_argument('--addr', dest='addr',
                        default=os.getenv(constants.ADDR_ENV, '0.0.0.0:8888'))

    return parser.parse_args()


def main():
    callargs = _get_callargs()

    if not callargs.default_redirect_url:
        _logger.e('%s env not set, use -default-redirect-url instead, program exit.', constants.DEFAULT_REDIRECT_URL)
        sys.exit(1)

    listen_addr = callargs.addr | split(':')
    if len(listen_addr) != __ADDRPAIR_LEN:
        _logger.e('addr must like 0.0.0.0:8888 format, program exit.')
        sys.exit(1)

    default_redirect_url = callargs.default_redirect_url
    redirect_rules = callargs.redirect_rules \
                     | split(';') \
                     | collect(lambda it: it | split('=') | as_tuple) \
                     | select(lambda it: len(it) == 2) \
                     | as_list

    redirect_dispatcher = RedirectDispatcher(default_redirect_url, redirect_rules)
    listen_port, listen_host = listen_addr[1] | as_int, listen_addr[0]
    reactor.listenTCP(listen_port, server.Site(redirect_dispatcher), interface=listen_host)

    _logger.w('waitting request on [tcp/%s].', callargs.addr)
    reactor.run()


if __name__ == '__main__':
    raise SystemExit(main())
