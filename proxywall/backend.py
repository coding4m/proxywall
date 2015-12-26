import abc
import json
import urlparse

import etcd
import jsonselect

from proxywall import loggers
from proxywall.commons import *
from proxywall.errors import *

__all__ = ["ProxyNode", "ProxyList", "Backend", "EtcdBackend"]


class ProxyNode(object):
    """

    """

    ALLOW_PROTOS = ['http', 'https']
    DEFAULT_PROTO = ALLOW_PROTOS[0]

    def __init__(self,
                 uuid=None, addr=None, port=None,
                 proto=None, network=None, weight=None):

        if proto and proto not in ProxyNode.ALLOW_PROTOS:
            raise ValueError('')

        self._uuid = uuid
        self._addr = addr
        self._port = port
        self._proto = proto if proto else ProxyNode.DEFAULT_PROTO
        self._network = network
        self._weight = weight if weight else -1

    def __eq__(self, other):
        if self is other:
            return True

        if not isinstance(other, ProxyNode):
            return False

        return self._uuid == other._uuid

    def __ne__(self, other):
        if self is other:
            return False

        if not isinstance(other, ProxyNode):
            return True

        return self._uuid != other._uuid

    def __hash__(self):
        return hash(self._uuid)

    @property
    def uuid(self):
        return self._uuid

    @property
    def addr(self):
        return self._addr

    @property
    def port(self):
        return self._port

    @property
    def proto(self):
        return self._proto

    @property
    def network(self):
        return self._network

    @property
    def weight(self):
        return self._weight

    def to_dict(self):
        return {'uuid': self._uuid, 'addr': self._addr, 'port': self._port,
                'proto': self._proto, 'network': self._network, 'weight': self._weight}

    @staticmethod
    def from_dict(dict_obj):
        return ProxyNode(uuid=jsonselect.select('.uuid', dict_obj),
                         addr=jsonselect.select('.addr', dict_obj),
                         port=jsonselect.select('.port', dict_obj),
                         proto=jsonselect.select('.proto', dict_obj),
                         network=jsonselect.select('.network', dict_obj),
                         weight=jsonselect.select('.weight', dict_obj))


class ProxyList(object):
    """

    """

    def __init__(self, name=None, nodes=None):
        self._name = name
        self._nodes = nodes if nodes else []

    @property
    def name(self):
        return self._name

    @property
    def nodes(self):
        return self._nodes

    def to_dict(self):
        return {"name": self._name,
                "nodes": self._nodes | collect(lambda node: node.to_dict()) | as_list}

    @staticmethod
    def from_dict(dict_obj):
        name = jsonselect.select('.name', dict_obj)
        nodes = jsonselect.select('.nodes', dict_obj)
        return ProxyList(name=name,
                         nodes=nodes | collect(lambda it: ProxyNode.from_dict(it)) | as_list)


class Backend(object):
    """

    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, backend_options):
        """

        :param backend_options:
        :return:
        """

        backend_url = urlparse.urlparse(backend_options)
        self._url = backend_url
        self._path = backend_url.path
        self._networks = urlparse.parse_qs(backend_url.query).get('network', [])

    def register_all(self, name, nodes):
        """

        :param name:
        :param nodes:
        :return:
        """
        for node in nodes:
            self.register(name, node)

    @abc.abstractmethod
    def register(self, name, node):
        """

        :param name:
        :param node:
        :return:
        """
        pass

    def unregister_all(self, name, nodes):
        """

        :param name:
        :param nodes:
        :return:
        """
        for node in nodes:
            self.unregister(name, node)

    @abc.abstractmethod
    def unregister(self, name, node):
        """

        :param name:
        :param node:
        :return:
        """
        pass

    @abc.abstractmethod
    def lookup(self, name):
        """

        :param name: domain name.
        :return: a releative ProxyList.
        """
        pass

    @abc.abstractmethod
    def lookall(self, name=None):
        """

        :param name:
        :return:
        """
        pass

    @abc.abstractmethod
    def watches(self, name=None, timeout=None, recursive=None):
        """

        :param name:
        :param timeout:
        :param recursive:
        :return:
        """
        pass


class EtcdBackend(Backend):
    """

    """

    NODES_SUBPATH = '@nodes'

    def __init__(self, *args, **kwargs):

        super(EtcdBackend, self).__init__(*args, **kwargs)
        host_pairs = [(addr | split(r':')) for addr in (self._url.netloc | split(','))]
        host_tuple = [(hostpair[0], int(hostpair[1])) for hostpair in host_pairs] | as_tuple

        self._client = etcd.Client(host=host_tuple, allow_reconnect=True)
        self._logger = loggers.get_logger('p.b.EtcdBackend')

    def _etcdkey(self, node_name, node_id=None):

        if not node_id:
            node_id = ''

        keys = [self._path] + \
               (node_name | split(r'\.') | reverse | as_list) + \
               [EtcdBackend.NODES_SUBPATH, node_id]
        return keys | join('/') | replace(r'/+', '/')

    def _rawkey(self, etcd_key):

        node_parts = etcd_key | split(r'/') | reverse | as_list
        if self._path and not self._path == '/':
            node_parts = node_parts[:-1]

        path_pattern = '[^.]*\.*{}\.*'.format(EtcdBackend.NODES_SUBPATH)
        return node_parts[1:-1] \
               | join('.') \
               | replace('\.+', '.') \
               | replace(path_pattern, '')

    def _etcdvalue(self, raw_value):
        return json.dumps(raw_value.to_dict())

    def _rawvalue(self, etcd_value):
        return ProxyNode.from_dict(json.loads(etcd_value))

    def register(self, name, node):

        if not name:
            raise BackendValueError('name must not be none or empty.')

        if not node or not node.uuid:
            raise BackendValueError('node or node.uuid must not be none or empty.')

        etcd_key = self._etcdkey(name, node_id=node.uuid)
        try:
            etcd_value = self._etcdvalue(node)
            self._client.set(etcd_key, etcd_value)
        except:
            self._logger.ex('register occur error.')
            raise BackendError

    def unregister(self, name, node):

        if not name:
            raise BackendValueError('name must not be none or empty.')

        if not node or not node.uuid:
            return

        etcd_key = self._etcdkey(name, node_id=node.uuid)
        try:

            self._client.delete(etcd_key)
        except etcd.EtcdKeyError:
            self._logger.w('unregister key %s not found, just ignore it', etcd_key)
        except:
            self._logger.ex('unregister occur error.')
            raise BackendError

    def lookup(self, name):

        if not name:
            raise BackendValueError('name must not be none or empty.')

        etcd_key = self._etcdkey(name)
        try:

            etcd_result = self._client.read(etcd_key, recursive=True)
            result_nodes = etcd_result.leaves \
                           | select(lambda it: it.value) \
                           | collect(lambda it: (self._rawkey(it.key), it.value)) \
                           | select(lambda it: it[0] == name) \
                           | collect(lambda it: self._rawvalue(it[1])) \
                           | select(lambda it: self._isavailable_proxy(it)) \
                           | as_list

            return ProxyList(name=name, nodes=result_nodes)

        except etcd.EtcdKeyError:
            self._logger.w('key %s not found, just ignore it.', etcd_key)
            return ProxyList(name=name)
        except:
            self._logger.ex('lookup key %s occurs error.', etcd_key)
            raise BackendError

    def lookall(self, name=None):

        etcd_key = self._etcdkey(name) if name else self._path
        try:

            etcd_result = self._client.read(etcd_key, recursive=True)
            return self._to_proxylists(etcd_result)

        except etcd.EtcdKeyError:
            self._logger.w('key %s not found, just ignore it.', etcd_key)
            return []
        except:
            self._logger.ex('lookall key %s occurs error.', etcd_key)
            raise BackendError

    def _isavailable_proxy(self, node):
        if not self._networks:
            return True
        return node.network in self._networks

    def _to_proxylists(self, result):

        results = {}
        self._collect_proxylist(result, results)

        for child in result.leaves:
            self._collect_proxylist(child, results)

        return results.items() \
               | collect(lambda it: ProxyList(name=it[0], nodes=it[1])) \
               | as_list

    def _collect_proxylist(self, result, results):

        if not result.value:
            return

        name = self._rawkey(result.key)
        node = self._rawvalue(result.value)

        if not self._isavailable_proxy(node):
            return

        if results.get(name):
            results[name].append(node)
        else:
            results[name] = [node]

    def watches(self, name=None, timeout=None, recursive=None):
        etcd_key = self._etcdkey(name) if name else self._path
        etcd_results = self._client.eternal_watch(etcd_key, recursive=recursive)
        for etcd_result in etcd_results:
            yield self._to_proxylists(etcd_result)
