import functools
import time

from proxywall import loggers

_logger = loggers.get_logger('p.s.supervise')


def supervise(min_seconds=None, max_seconds=None):
    """

    :param min_seconds:
    :param max_seconds:
    :return:
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapped(*args, **kwargs):

            retry_seconds = min_seconds
            next_retry_seconds = retry_seconds

            while True:
                try:
                    return function(*args, **kwargs)
                except KeyboardInterrupt:
                    _logger.w('thread interrupted, stop supervise and exit.')
                    return None
                except:
                    _logger.ex('function call occurs error.')
                    _logger.w('sleep %d seconds and retry again.', retry_seconds)

                    time.sleep(retry_seconds)
                    next_retry_seconds *= 2
                    if next_retry_seconds > max_seconds:
                        next_retry_seconds = min_seconds
                    retry_seconds = next_retry_seconds

        return wrapped

    return decorator
