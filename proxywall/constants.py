"""

"""
import sys


class _Constants(object):
    """

    """

    class ConstantError(TypeError):
        pass

    def __setattr__(self, name, value):
        if self.__dict__.has_key(name):
            raise self.ConstantError("Can't rebind constant (%s)" % name)

        self.__dict__[name] = value


_constants = _Constants()
_constants.BACKEND_ENV = 'PROXYWALL_BACKEND'
_constants.NETWORKS_ENV = 'PROXYWALL_NETWORKS'
_constants.TEMPLATE_SRC_ENV = 'PROXYWALL_TEMPLATE_SRC'
_constants.TEMPLATE_DEST_ENV = 'PROXYWALL_TEMPLATE_DEST'
_constants.PREV_CMD_ENV = 'PROXYWALL_PREV_CMD'
_constants.POST_CMD_ENV = 'PROXYWALL_POST_CMD'
_constants.DOCKER_URL_ENV = 'PROXYWALL_DOCKER_URL'
_constants.DOCKER_TLSCA_ENV = 'PROXYWALL_DOCKER_TLSCA'
_constants.DOCKER_TLSKEY_ENV = 'PROXYWALL_DOCKER_TLSKEY'
_constants.DOCKER_TLSCERT_ENV = 'PROXYWALL_DOCKER_TLSCERT'
_constants.DOCKER_TLSVERIFY_ENV = 'PROXYWALL_DOCKER_TLSVERIFY'
sys.modules[__name__] = _constants
