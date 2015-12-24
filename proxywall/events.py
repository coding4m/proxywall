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
    _handle_containers(backend, _get_containers(client))
    for _ in events:
        # TODO when container destroy, we may lost the opportunity to unregister the container.
        # it may cause performance issue.
        _handle_containers(backend, _get_containers(client))


def _get_containers(client):
    return client.containers(quiet=True, all=True) \
           | collect(lambda container: _jsonselect(container, '.Id')) \
           | collect(lambda container_id: _get_container(client, container_id))


def _get_container(client, container_id):
    return client.inspect_container(container_id)


def _handle_containers(backend, containers):
    register_proxy_datas, unregister_proxy_datas = ([], [],)
    for container in containers:
        _handle_container(backend, container, register_proxy_datas, unregister_proxy_datas)

    # unregister proxy first.
    for proxy_data in unregister_proxy_datas:
        _unregister_proxy(backend, proxy_data[0])

    proxy_groups = {}
    for proxy_data in register_proxy_datas:

        try:
            proxy_node = ProxyNode(addr=proxy_data[1],
                                   port=proxy_data[2],
                                   proto=proxy_data[3],
                                   network=proxy_data[4],
                                   weight=proxy_data[5])
        except:
            _logger.ex('generate proxy node failed, just ignore it.')
            continue

        proxy_name = proxy_data[0]
        if not proxy_groups.get(proxy_name):
            proxy_groups[proxy_name] = [proxy_node]
        else:
            proxy_groups[proxy_name].append(proxy_node)

    # now register proxy.
    for proxy_item in proxy_groups.items():
        _register_proxy(backend, proxy_item[0], proxy_item[1])


def _handle_container(backend, container, register_proxy_datas, unregister_proxy_datas):
    try:

        container_environments = _jsonselect(container, '.Config .Env') \
                                 | collect(lambda env: env | split(r'=', maxsplit=1)) \
                                 | collect(lambda env: env | as_tuple) \
                                 | as_tuple \
                                 | as_dict

        proxy_host = _jsonselect(container_environments, '.VHOST')
        proxy_port = _jsonselect(container_environments, '.VPORT')
        if not proxy_host or not proxy_port:
            return

        container_status = _jsonselect(container, '.State .Status')
        if container_status in ['paused', 'exited']:
            unregister_proxy_datas.append((proxy_host,))
            return

        proxy_network = _jsonselect(container_environments, '.VNETWORK')
        if not proxy_network:
            return

        # it may be occurs error when proxy_network is a malicious word.
        proxy_addr = _jsonselect(container, '.NetworkSettings .Networks .%s .IPAddress'.format(proxy_network))
        if not proxy_addr:
            return

        proxy_proto = _jsonselect(container_environments, '.VPROTO')
        proxy_weight = _jsonselect(container_environments, '.VWEIGHT')
        register_proxy_datas.append((proxy_host, proxy_addr, proxy_port,
                                     proxy_proto, proxy_network, proxy_weight,))

    except:
        _logger.ex('handle container occurs error, just ignore it.')


def _jsonselect(obj, selector):
    return jsonselect.select(selector, obj)


def _register_proxy(backend, name, nodes):
    _logger.w('register proxy[virtual_host=%s] to backend.', name)
    backend.register(name, nodes)


def _unregister_proxy(backend, name):
    _logger.w('unregister proxy[virtual_host=%s] from backend.', name)
    backend.unregister(name)
