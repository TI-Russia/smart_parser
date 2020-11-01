from django_elasticsearch_dsl.signals import RealTimeSignalProcessor

class ElasticSignalProcessor: RealTimeSignalProcessor
    def setup(self):
        super().setup