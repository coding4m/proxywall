import abc
import json
import urlparse

import etcd
import jsonselect

from proxywall import loggers
from proxywall.commons import *
from proxywall.errors import *

__all__ = ["ProxyNode", "ProxyRecord", "Backend", "EtcdBackend"]


class ProxyNode(object):
    """

    """

    _ALLOW_PROXY_PROTOS = ['http', 'https']
    _DEFAULT_PROXY_PROTO = 'http'

    def __init__(self, addr=None, port=None, proto=None, network=None, weight=None):
        """

        :param addr:
        :param port:
        :param ttl:
        :return:
        """

        if proto and proto not in ProxyNode._ALLOW_PROXY_PROTOS:
            raise ValueError('')

        self._addr = addr
        self._port = port if isinstance(port, int) else (port | as_int)
        self._proto = proto if proto else ProxyNode._DEFAULT_PROXY_PROTO
        self._network = network
        self._weight = weight if weight else -1

    def __cmp__(self, other):
        # TODO
        pass

    @property
    def addr(self):
        """

        :return:
        """
        return self._addr

    @property
    def port(self):
        """

        :return:
        """
        return self._port

    @property
    def proto(self):
        """

        :return:
        """
        return self._proto

    @property
    def network(self):
        """

        :return:
        """
        return self._network

    @property
    def weight(self):
        """

        :return:
        """
        return self._weight

    def to_dict(self):
        return {'addr': self._addr, 'port': self._port,
                'proto': self._proto, 'network': self._network, 'weight': self._weight}

    @staticmethod
    def from_dict(dict_obj):
        return ProxyNode(addr=jsonselect.select('.addr', dict_obj),
                         port=jsonselect.select('.port', dict_obj),
                         proto=jsonselect.select('.proto', dict_obj),
                         network=jsonselect.select('.network', dict_obj),
                         weight=jsonselect.select('.weight', dict_obj))


class ProxyRecord(object):
    def __init__(self, name=None, ttl=-1, nodes=None):
        """

        :param name:
        :param nodes:
        :return:
        """

        self._name = name
        self._ttl = ttl if ttl else -1
        self._nodes = nodes if nodes else []

    @property
    def name(self):
        return self._name

    @property
    def ttl(self):
        return self._ttl

    @property
    def nodes(self):
        return self._nodes

    def to_dict(self):
        return {"name": self._name, "ttl": self._ttl,
                "nodes": self._nodes | collect(lambda node: node.to_dict()) | as_list}


class Backend(object):
    """

    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, backend_options=None):
        """

        :param backend_options:
        :return:
        """

        backend_url = urlparse.urlparse(backend_options)
        backend_patterns = urlparse.parse_qs(backend_url.query).get('pattern', [])
        backend_networks = urlparse.parse_qs(backend_url.query).get('network', [])
        self._url = backend_url
        self._patterns = backend_patterns
        self._networks = backend_networks

    def supports(self, name):
        """

        :param name:
        :return:
        """

        if not name:
            return False

        return self._patterns | any(lambda pattern: name.endswith(pattern))

    @abc.abstractmethod
    def register(self, name, nodes, ttl=None):
        """

        :param name:
        :param nodes:
        :param ttl:
        :return:
        """
        pass

    @abc.abstractmethod
    def unregister(self, name):
        """

        :param name: domain name.
        :return:
        """
        pass

    @abc.abstractmethod
    def lookup(self, name):
        """

        :param name: domain name.
        :return: a releative ProxyRecord.
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

    def __init__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """

        super(EtcdBackend, self).__init__(*args, **kwargs)
        host_pairs = [(addr | split(r':')) for addr in (self._url.netloc | split(','))]
        host_tuple = [(hostpair[0], int(hostpair[1])) for hostpair in host_pairs] | as_tuple

        self._client = etcd.Client(host=host_tuple, allow_reconnect=True)
        self._logger = loggers.get_logger('p.b.EtcdBackend')

    def _etcdkey(self, name):
        """

        :param name: domain format string, like api.dnswall.io
        :return: a etcd key format string, /io/dnswall/api
        """

        if not name:
            return [self._url.path] | join('/') | replace(r'/+', '/')
        else:
            keys = [self._url.path] + (name | split(r'\.') | reverse | as_list)
            return keys | join('/') | replace(r'/+', '/')

    def _rawname(self, key):
        """

        :param key: etcd key, like /io/dnswall/api
        :return: domain format string, like api.dnswall.io
        """

        raw_key = key if key.endswith('/') else key + '/'
        raw_names = raw_key | split(r'/') | reverse | as_list
        return raw_names[1:-1] | join('.') | replace('\.+', '.')

    def register(self, name, nodes, ttl=None):

        if not self.supports(name):
            raise BackendError("name={} unsupport.".format(name))

        try:

            nodelist = nodes | collect(lambda node: node.to_dict()) | as_list
            self._client.set(self._etcdkey(name), json.dumps(nodelist))
        except Exception as e:
            # TODO
            print(e)
            raise BackendError

    def unregister(self, name):

        if not name:
            raise ValueError('name must not be none or empty.')

        try:

            self._client.delete(self._etcdkey(name))
        except etcd.EtcdKeyError:
            pass
        except:
            # TODO
            raise BackendError

    def lookup(self, name):

        if not self.supports(name):
            raise BackendError("name={} unsupport.".format(name))

        try:

            result = self._client.get(self._etcdkey(name))
            if not result.value:
                return ProxyRecord(name=name)

            return self._as_record(name, result.ttl, json.loads(result.value))
        except etcd.EtcdKeyError:
            return ProxyRecord(name=name)
        except Exception as e:
            # TODO
            print(e)
            raise BackendError

    def lookall(self, name=None):
        try:

            result = self._client.read(self._etcdkey(name), recursive=True)
            return self._as_records(result)
        except etcd.EtcdKeyError:
            return []
        except Exception as e:
            print(e)
            pass

    def _as_record(self, name, ttl, nodelist):
        return ProxyRecord(name=name,
                           ttl=ttl,
                           nodes=nodelist | collect(lambda node: ProxyNode.from_dict(node)) | as_list)

    def _as_records(self, result):

        records = []
        self._append_records(result, records)

        for child in result.children:
            self._append_records(child, records)
        return records

    def _append_records(self, result, records):

        if result.value:
            nodelist = json.loads(result.value)
            records.append(self._as_record(self._rawname(result.key), result.ttl, nodelist))

    def watches(self, name=None, timeout=None, recursive=None):
        results = self._client.watch(self._etcdkey(name), timeout=timeout, recursive=recursive)
        for result in results:
            yield self._as_records(result)
