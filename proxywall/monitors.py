"""

"""

import os

from proxywall import commands
from proxywall import loggers
from proxywall import supervisor
from proxywall import template

_logger = loggers.getlogger('p.m.Loop')


def loop(backend, prev_cmd=None, post_cmd=None, template_src=None, template_dest=None):
    """

    :param backend:
    :param prev_cmd:
    :param post_cmd:
    :param template_src:
    :param template_dest:
    :return:
    """
    supervisor.supervise(min_seconds=2, max_seconds=64)(_loop_proxy)(backend,
                                                                     prev_cmd,
                                                                     post_cmd,
                                                                     template_src,
                                                                     template_dest)


def _loop_proxy(backend, prev_cmd, post_cmd, template_src, template_dest):
    # watches event first.
    _events = backend.watches(recursive=True)
    _handle_proxy(backend, prev_cmd, post_cmd, template_src, template_dest)

    # signal
    for _ in _events:
        _handle_proxy(backend, prev_cmd, post_cmd, template_src, template_dest)


def _handle_proxy(backend, prev_cmd, post_cmd, template_src, template_dest):
    # write prev command if neccesary.
    if prev_cmd:
        _logger.w('run [prev_cmd=%s].', template_dest, prev_cmd)
        commands.run(prev_cmd)

    proxy_details = backend.lookall()
    template_in = _read_src_template(template_src)
    template_out = template.render(template_in, context={'proxy_details': proxy_details})

    _logger.w('write template to %s.', template_dest)
    _write_dest_template(template_dest, template_out)

    _logger.w('run [post_cmd=%s].', post_cmd)
    rc, cmdout, cmderr = commands.run(post_cmd)
    if rc != 0:
        _logger.w('run %s with exitcode %s.', post_cmd, rc)


def _read_src_template(template_src):
    template_in = ''

    with open(template_src, 'r') as f:
        while True:
            template_data = f.read(1024)
            if not template_data:
                break
            template_in += template_data

    return template_in


def _write_dest_template(template_dest, template_out):
    template_dir = os.path.dirname(template_dest)
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    with open(template_dest, 'w') as f:
        f.write(template_out)
