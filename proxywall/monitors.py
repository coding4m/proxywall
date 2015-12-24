"""

"""

from proxywall import loggers
from proxywall import supervisor
from proxywall import template

_logger = loggers.get_logger('p.m.Loop')


def loop(backend=None,
         template_signal=None,
         template_source=None,
         template_destination=None):
    """

    :param backend:
    :param template_signal:
    :param template_source:
    :param template_destination:
    :return:
    """
    supervisor.supervise(min_seconds=2, max_seconds=64)(_loop_proxies)(backend,
                                                                       template_signal,
                                                                       template_source,
                                                                       template_destination)


def _loop_proxies(backend, template_signal, template_source, template_destination):
    proxy_events = backend.watches(recursive=True)
    _handle_proxies(backend, template_signal, template_source, template_destination)
    # signal
    for _ in proxy_events:
        _handle_proxies(backend, template_signal, template_source, template_destination)


def _handle_proxies(backend, template_signal, template_source, template_destination):
    proxy_records = backend.lookall()
    template.render(template_source, context={'proxy_records': proxy_records})
