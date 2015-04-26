# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.contrib.auth import get_backends
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import importlib

import e89_syncing.syncing_utils
import DataSyncHelper
import json
import sys

@csrf_exempt
def get_data_from_server(request, identifier = None):
    if request.method != 'POST':
        return HttpResponse("")
    data = e89_syncing.syncing_utils._get_user_data(request)

    print >>sys.stderr, 'GET DATA FROM SERVER: RECEIVED ' + str(data)
    token = data["token"]

    if identifier is not None:
        response = DataSyncHelper.getModifiedDataForIdentifier(token = token, parameters = data, identifier = identifier)
    else:
        timestamp = data["timestamp"]
        response = DataSyncHelper.getModifiedData(token = token, timestamp = timestamp)
    print >>sys.stderr, 'GET DATA FROM SERVER: RESPONDED ' + str(response)

    return e89_syncing.syncing_utils._generate_user_response(json.dumps(response,ensure_ascii=False))

@csrf_exempt
def send_data_to_server(request):
    if request.method != 'POST':
        return HttpResponse("")

    data = e89_syncing.syncing_utils._get_user_data(request)

    print >>sys.stderr, 'SEND DATA TO SERVER: RECEIVED ' + str(data)
    token = data["token"]
    timestamp = data["timestamp"]
    if data.has_key('registration_id'):
        device_id = data['registration_id']
    else:
        device_id = data['device_id']

    response = DataSyncHelper.saveNewData(token = token, timestamp = timestamp, device_id = device_id, data = data, files = request.FILES)

    print >>sys.stderr, 'SEND DATA TO SERVER: RESPONDED ' + str(response)
    return e89_syncing.syncing_utils._generate_user_response(json.dumps(response,ensure_ascii=False))

@csrf_exempt
def authenticate(request):
    ''' View para autenticação. Deve receber como parâmetro (via POST), um json no formato:

        {
            "username": "...",
            "senha": "..."
        }

    '''

    response = {}
    if request.method == "POST":
        data = e89_syncing.syncing_utils._get_user_data(request)

        username = data["username"]
        password = data["password"]

        module_name,class_name = getattr(settings,'SYNC_AUTHENTICATION','e89_syncing.authentication.BaseSyncAuthentication').rsplit('.',1)
        mod = importlib.import_module(module_name)
        SyncAuthentication = getattr(mod, class_name)
        response = SyncAuthentication().authenticate(username,password)

    return e89_syncing.syncing_utils._generate_user_response(json.dumps(response,ensure_ascii=False))

