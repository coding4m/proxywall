"""

"""

import os
import pipes
import select as ioselect
import shlex
import subprocess

from proxywall import loggers
from proxywall.commons import *

_logger = loggers.get_logger('p.commands')


def run(cmd, close_fds=True, use_executable=None, use_shell=False, data=None, binary_data=False):
    """

    :param cmd:
    :param close_fds:
    :param use_executable:
    :param use_shell:
    :param data:
    :param binary_data:
    :return:
    """

    cmd_args = cmd
    cmd_shell = False

    if isinstance(cmd, list) and use_shell:
        cmd_args = [pipes.quote(x) for x in cmd] | join(' ')
        cmd_shell = True
    elif isinstance(cmd, basestring) and use_shell:
        cmd_shell = True
    elif isinstance(cmd, basestring):
        cmd_args = shlex.split(cmd.encode('utf-8'))
    else:
        raise ValueError('cmd to run must be list or string')

    if not cmd_shell:
        cmd_args = [os.path.expandvars(os.path.expanduser(x)) for x in cmd_args]

    std_in = None
    if data:
        std_in = subprocess.PIPE

    kwargs = dict(
        executable=use_executable,
        close_fds=close_fds,
        shell=cmd_shell,
        stdin=std_in,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:

        cmd_proc = subprocess.Popen(cmd_args, **kwargs)

        std_out = ''
        std_err = ''
        rpipes = [cmd_proc.stdout, cmd_proc.stderr]

        if data:
            if not binary_data:
                data += '\n'
            cmd_proc.stdin.write(data)
            cmd_proc.stdin.close()

        while True:

            rfd, wfd, efd = ioselect.select(rpipes, [], rpipes, 1)
            if cmd_proc.stdout in rfd:
                dat = os.read(cmd_proc.stdout.fileno(), 2048)
                std_out += dat
                if dat == '':
                    rpipes.remove(cmd_proc.stdout)
            if cmd_proc.stderr in rfd:
                dat = os.read(cmd_proc.stderr.fileno(), 2048)
                std_err += dat
                if dat == '':
                    rpipes.remove(cmd_proc.stderr)

            # only break out if no pipes are left to read or
            # the pipes are completely read and
            # the process is terminated
            if (not rpipes or not rfd) and cmd_proc.poll() is not None:
                break
            # No pipes are left to read but process is not yet terminated
            # Only then it is safe to wait for the process to be finished
            # NOTE: Actually cmd.poll() is always None here if rpipes is empty
            elif not rpipes and cmd_proc.poll() == None:
                cmd_proc.wait()
                # The process is terminated. Since no pipes to read from are
                # left, there is no need to run select() again.
                break

        cmd_proc.stdout.close()
        cmd_proc.stderr.close()
        return cmd_proc.returncode, std_out, std_err
    except Exception as e:
        _logger.ex('''run command['%s'] occurs error.''', cmd)
        raise e
