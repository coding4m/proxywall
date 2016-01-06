"""

"""
import docker
import jsonselect

from proxywall import loggers
from proxywall import supervisor
from proxywall.backend import *
from proxywall.commons import *
from proxywall.errors import *

_logger = loggers.getlogger('p.e.Loop')


def loop(backend,
         docker_url,
         docker_tls_verify=False,
         docker_tls_ca=None,
         docker_tls_key=None,
         docker_tls_cert=None):
    """

    :param backend:
    :param docker_url:
    :param docker_tls_verify:
    :param docker_tls_ca:
    :param docker_tls_key:
    :param docker_tls_cert:
    :return:
    """

    # TODO
    _client = docker.AutoVersionClient(base_url=docker_url)
    _logger.w('start and supervise event loop.')
    supervisor.supervise(min_seconds=2, max_seconds=64)(_event_loop)(backend, _client)


def _event_loop(backend, client):
    # consume real time events first.
    _events = client.events(decode=True, filters={'event': ['destroy', 'die', 'start', 'stop', 'pause', 'unpause']})

    # now loop containers.
    _handle_containers(backend, _get_containers(client))
    for _event in _events:
        # TODO when container destroy, we may lost the opportunity to unregister the container.
        _container = _get_container(client, _jsonselect(_event, '.id'))
        _handle_container(backend, _container)


def _get_containers(client):
    return client.containers(quiet=True, all=True) \
           | collect(lambda it: _jsonselect(it, '.Id')) \
           | collect(lambda it: _get_container(client, it))


def _get_container(client, container_id):
    return client.inspect_container(container_id)


def _handle_containers(backend, containers):
    for container in containers:
        _handle_container(backend, container)


def _handle_container(backend, container):
    try:

        container_id = _jsonselect(container, '.Id')
        container_status = _jsonselect(container, '.State .Status')

        # ignore tty container.
        is_tty_container = _jsonselect(container, '.Config .Tty')
        if is_tty_container:
            _logger.w('ignore tty container[id=%s]', container_id)
            return

        container_environments = _jsonselect(container, '.Config .Env')
        if not container_environments:
            return

        container_environments = container_environments \
                                 | collect(lambda it: it | split(r'=', maxsplit=1)) \
                                 | collect(lambda it: it | as_tuple) \
                                 | as_tuple \
                                 | as_dict

        proxy_host = _jsonselect(container_environments, '.VHOST')
        proxy_port = _jsonselect(container_environments, '.VPORT')
        if not proxy_host or not proxy_port:
            return

        proxy_network = _jsonselect(container_environments, '.VNETWORK')
        if not proxy_network:
            return

        if container_status in ['paused', 'exited']:
            _unregister_proxy(backend, proxy_host, ProxyNode(uuid=container_id))

        # it may be occurs error when proxy_network is a malicious word.
        proxy_addr_path = '.NetworkSettings .Networks .{} .IPAddress'.format(proxy_network)
        proxy_addr = _jsonselect(container, proxy_addr_path)
        if not proxy_addr:
            return

        proxy_proto = _jsonselect(container_environments, '.VPROTO')
        proxy_weight = _jsonselect(container_environments, '.VWEIGHT')

        proxy_node = ProxyNode(uuid=container_id, addr=proxy_addr, port=proxy_port,
                               proto=proxy_proto, network=proxy_network, weight=proxy_weight)

        _register_proxy(backend, proxy_host, proxy_node)

    except BackendValueError:
        _logger.ex('handle container occurs BackendValueError, just ignore it.')
    except BackendError as e:
        raise e
    except:
        _logger.ex('handle container occurs error, just ignore it.')


def _jsonselect(obj, selector):
    return jsonselect.select(selector, obj)


def _register_proxy(backend, proxy_host, proxy_node):
    _logger.w('register proxy[virtual_host=%s] to backend.', proxy_host)
    backend.register(proxy_host, proxy_node)


def _unregister_proxy(backend, proxy_host, proxy_node):
    _logger.w('unregister proxy[virtual_host=%s] from backend.', proxy_host)
    backend.unregister(proxy_host, proxy_node)
