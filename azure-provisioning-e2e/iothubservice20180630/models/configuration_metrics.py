# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ConfigurationMetrics(Model):
    """Configuration Metrics.

    :param results:
    :type results: dict[str, long]
    :param queries:
    :type queries: dict[str, str]
    """

    _attribute_map = {
        'results': {'key': 'results', 'type': '{long}'},
        'queries': {'key': 'queries', 'type': '{str}'},
    }

    def __init__(self, results=None, queries=None):
        super(ConfigurationMetrics, self).__init__()
        self.results = results
        self.queries = queries
