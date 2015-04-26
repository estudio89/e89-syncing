# -*- coding: utf-8 -*-
from django.conf.urls import patterns, include, url

urlpatterns = patterns('e89_syncing.views',
    (r'^authenticate/', 'authenticate'),
    (r'^get-data-from-server/$', 'get_data_from_server'),
    (r'^get-data-from-server/(?P<identifier>\w+)/$', 'get_data_from_server'),
    (r'^send-data-to-server/', 'send_data_to_server'),
)