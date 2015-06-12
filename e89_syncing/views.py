# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.contrib.auth import get_backends
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from django.shortcuts import get_object_or_404
import importlib

import e89_security.tools
import DataSyncHelper
import json
import sys

@csrf_exempt
def get_data_from_server(request, identifier = None):
    if request.method != 'POST':
        return HttpResponse("")
    data = e89_security.tools._get_user_data(request, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False))

    print >>sys.stderr, 'GET DATA FROM SERVER: RECEIVED ' + str(data)
    token = data["token"]
    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    try:
        user = UserModel.objects.get(**{settings.SYNC_TOKEN_ATTR:token,settings.SYNC_TOKEN_ATTR + "__isnull":False})
    except UserModel.DoesNotExist:
        response = DataSyncHelper.getEmptyModifiedDataResponse()
    else:
        timestamp = data.get("timestamp") # maintains compatibility
        timestamps = data.get("timestamps",{})
        if identifier is not None:
            response = DataSyncHelper.getModifiedDataForIdentifier(user = user, parameters = data, identifier = identifier, timestamps = timestamps)
        else:
            assert timestamp is not None or timestamps != {}, "Timestamp was not sent along with data."
            response = DataSyncHelper.getModifiedData(user = user, timestamp = timestamp, timestamps = timestamps)

    print >>sys.stderr, 'GET DATA FROM SERVER: RESPONDED ' + str(response)

    return e89_security.tools._generate_user_response(response, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False))

@csrf_exempt
def send_data_to_server(request):
    if request.method != 'POST':
        return HttpResponse("")

    data = e89_security.tools._get_user_data(request, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False))

    print >>sys.stderr, 'SEND DATA TO SERVER: RECEIVED ' + str(data)
    token = data["token"]
    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    user = get_object_or_404(UserModel,**{settings.SYNC_TOKEN_ATTR:token})

    timestamp = data.get("timestamp") # maintains compatibility
    timestamps = data.get("timestamps",{})
    assert timestamp is not None or timestamps != {}, "Timestamp was not sent along with data."
    if data.has_key('registration_id'):
        device_id = data['registration_id']
    else:
        device_id = data['device_id']

    response = DataSyncHelper.saveNewData(user = user, timestamp = timestamp, timestamps = timestamps, device_id = device_id, data = data, files = request.FILES)

    print >>sys.stderr, 'SEND DATA TO SERVER: RESPONDED ' + str(response)
    return e89_security.tools._generate_user_response(response, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False))

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
        data = e89_security.tools._get_user_data(request, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False))

        username = data["username"]
        password = data["password"]

        module_name,class_name = getattr(settings,'SYNC_AUTHENTICATION','e89_syncing.authentication.BaseSyncAuthentication').rsplit('.',1)
        mod = importlib.import_module(module_name)
        SyncAuthentication = getattr(mod, class_name)
        response = SyncAuthentication().authenticate(username,password)

    return e89_security.tools._generate_user_response(response, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False))

