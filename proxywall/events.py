"""

"""
import sched
import time

import docker
import jsonselect

from proxywall import loggers
from proxywall import supervisor
from proxywall.backend import *
from proxywall.commons import *
from proxywall.errors import *

_logger = loggers.getlogger('p.e.Loop')


def loop(backend, docker_url):
    """

    :param backend:
    :param docker_url:
    :return:
    """

    _logger.w('start and supervise event loop.')

    client = docker.AutoVersionClient(base_url=docker_url)
    supervisor.supervise(min_seconds=2, max_seconds=64)(_event_loop)(backend, client)


def _event_loop(backend, client):
    _heartbeat_containers(backend, client)

    _schd = sched.scheduler(time.time, time.sleep)
    while True:
        _schd.enter(30, 0, _heartbeat_containers, (backend, client))
        _schd.run()


def _heartbeat_containers(backend, client):
    # list all running containers.
    containers = client.containers(quiet=True) \
                 | collect(lambda it: _jsonselect(it, '.Id')) \
                 | collect(lambda it: client.inspect_container(it))
    for container in containers:
        _heartbeat_container(backend, container)


def _heartbeat_container(backend, container):
    try:

        container_id = _jsonselect(container, '.Id')
        container_status = _jsonselect(container, '.State .Status')

        # ignore tty container.
        is_tty_container = _jsonselect(container, '.Config .Tty')
        if is_tty_container:
            _logger.w('ignore tty container[id=%s, status=%s]', container_id, container_status)
            return

        container_environments = _jsonselect(container, '.Config .Env')
        if not container_environments:
            return

        container_environments = container_environments \
                                 | collect(lambda it: it | split(r'=', maxsplit=1)) \
                                 | collect(lambda it: it | as_tuple) \
                                 | as_tuple \
                                 | as_dict

        proxy_port = _jsonselect(container_environments, '.VPORT')
        proxy_domain = _jsonselect(container_environments, '.VHOST')
        proxy_network = _jsonselect(container_environments, '.VNETWORK')
        if not proxy_domain or not proxy_port or not proxy_network:
            return

        # it may be occurs error when proxy_network is a malicious word.
        proxy_addr_selector = '.NetworkSettings .Networks .{} .IPAddress'.format(proxy_network)
        proxy_addr = _jsonselect(container, proxy_addr_selector)
        if not proxy_addr:
            return

        proxy_proto = _jsonselect(container_environments, '.VPROTO')
        proxy_weight = _jsonselect(container_environments, '.VWEIGHT')

        _logger.d('heartbeat container[id=%s, vhost=%s] to backend.', container_id, proxy_domain)
        proxy_node = ProxyNode(uuid=container_id, addr=proxy_addr, port=proxy_port,
                               proto=proxy_proto, network=proxy_network, weight=proxy_weight)

        backend.register(proxy_domain, proxy_node, ttl=60)

    except BackendValueError:
        _logger.ex('heartbeat container occurs BackendValueError, just ignore it.')
    except BackendError as e:
        raise e
    except:
        _logger.ex('heartbeat container occurs error, just ignore it.')


def _jsonselect(obj, selector):
    return jsonselect.select(selector, obj)
