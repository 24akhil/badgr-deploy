from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from pathway.public_api import PathwayElementJson

json_patterns = [
    url(r'^pathways/(?P<pathway_slug>[^/]+)/(?P<element_slug>[^/]+)$', PathwayElementJson.as_view(), name='pathway_element_json'),
]

urlpatterns = format_suffix_patterns(json_patterns, allowed=['json'])
