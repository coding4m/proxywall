"""

"""

import os

from proxywall import commands
from proxywall import loggers
from proxywall import supervisor
from proxywall import template

_logger = loggers.get_logger('p.m.Loop')


def loop(backend=None,
         prev_command=None,
         post_command=None,
         template_source=None,
         template_destination=None):
    """

    :param backend:
    :param prev_command:
    :param post_command:
    :param template_source:
    :param template_destination:
    :return:
    """
    supervisor.supervise(min_seconds=2, max_seconds=64)(_loop_proxies)(backend,
                                                                       prev_command,
                                                                       post_command,
                                                                       template_source,
                                                                       template_destination)


def _loop_proxies(backend,
                  prev_command,
                  post_command,
                  template_source,
                  template_destination):
    # watches event first.
    _events = backend.watches(recursive=True)
    _handle_proxies(backend, prev_command, post_command,
                    template_source, template_destination)

    # signal
    for _ in _events:
        _handle_proxies(backend, prev_command, post_command,
                        template_source, template_destination)


def _handle_proxies(backend,
                    prev_command,
                    post_command,
                    template_source,
                    template_destination):
    # write prev command if neccesary.
    if prev_command:
        commands.run(prev_command)

    proxylists = backend.lookall()

    template_dir = os.path.dirname(template_destination)
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    template_in = ''
    with open(template_source, 'r') as f:
        while True:
            template_data = f.read(1024)
            if not template_data:
                break
            template_in += template_data

    template_out = template.render(template_in, context={'proxy_records': proxylists})
    with open(template_destination, 'w') as f:
        f.write(template_out)

    commands.run(post_command)
