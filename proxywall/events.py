"""

"""
import docker
import jsonselect

from proxywall import loggers
from proxywall import supervisor
from proxywall.backend import *
from proxywall.commons import *

_logger = loggers.get_logger('d.e.Loop')


def loop(backend=None,
         docker_url=None,
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
    events = client.events(decode=True, filters={'event': ['start', 'stop', 'pause', 'unpause']})

    # now loop containers.
    _handle_proxy_nodes(backend, _get_containers(client))
    for _ in events:
        # TODO when container destroy, we may lost the opportunity to unregister the container.
        _handle_proxy_nodes(backend, _get_containers(client))


def _get_containers(client):
    return client.containers(quiet=True, all=True) \
           | collect(lambda container: _jsonselect(container, '.Id')) \
           | collect(lambda container_id: _get_container(client, container_id))


def _get_container(client, container_id):
    return client.inspect_container(container_id)


def _handle_proxy_nodes(backend, containers):
    register_proxy_records = []
    unregister_proxy_records = []
    for container in containers:
        _handle_container(backend, container, register_proxy_records, unregister_proxy_records)


def _handle_container(backend, container, register_proxy_records, unregister_proxy_records):
    container_environments = _jsonselect(container, '.Config .Env') \
                             | collect(lambda env: env | split(r'=', maxsplit=1)) \
                             | collect(lambda env: env | as_tuple) \
                             | as_tuple \
                             | as_dict

    environment_vhost = _jsonselect(container_environments, '.VHOST')
    environment_vport = _jsonselect(container_environments, '.VPORT')
    if not environment_vhost or not environment_vport:
        return

    container_status = _jsonselect(container, '.State .Status')
    if container_status in ['paused', 'exited']:
        unregister_proxy_records.append(environment_vhost)
        return

    environment_vnetwork = _jsonselect(container_environments, '.VNETWORK')
    if not environment_vnetwork:
        return

    container_network = _jsonselect(container, '.NetworkSettings .Networks .%s'.format(environment_vnetwork))
    if not container_network:
        return

    envrionment_vproto = _jsonselect(container_environments, '.VPROTO')
    environment_vweight = _jsonselect(container_environments, '.VWEIGHT')

    _register_proxy_nodes(backend, environment_vhost, container_networks)


def _jsonselect(obj, selector):
    return jsonselect.select(selector, obj)


def _register_proxy_nodes(backend, vhost, container_networks):
    _logger.w('register container[domain_name=%s] to backend.', vhost)

    namespecs = container_networks \
                | collect(lambda item: (_jsonselect(item, '.IPAddress'),
                                        _jsonselect(item, '.GlobalIPv6Address'),)) \
                | collect(lambda item: ProxyNode(host=item[0], port=item[1])) \
                | as_list

    backend.register(vhost, namespecs)


def _unregister_proxy_nodes(backend, container_domain):
    _logger.w('unregister container[domain_name=%s] from backend.', container_domain)
    backend.unregister(container_domain)
