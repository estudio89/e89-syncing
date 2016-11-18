# -*- coding: utf-8 -*-
from django.conf.urls import url
import e89_syncing.views

urlpatterns = [
    url(r'^authenticate/', e89_syncing.views.authenticate),
    url(r'^get-data-from-server/$', e89_syncing.views.get_data_from_server),
    url(r'^get-data-from-server/(?P<identifier>\w+)/$', e89_syncing.views.get_data_from_server),
    url(r'^send-data-to-server/', e89_syncing.views.send_data_to_server),
]