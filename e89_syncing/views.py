# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.contrib.auth import get_backends
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.apps import apps
from django.shortcuts import get_object_or_404
import importlib

import e89_security.tools
import e89_syncing.syncing_utils
import DataSyncHelper
import json
import sys

def _is_gzip_active(request):
    return request.META.get('HTTP_X_E89_SYNCING_VERSION', '1.0.4') >= '1.0.5'

@csrf_exempt
def get_data_from_server(request, identifier = None):
    if request.method != 'POST':
        return HttpResponse("")

    if not request.user.is_authenticated():
        data = e89_security.tools._get_user_data(request, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False), gzip_active=_is_gzip_active(request))
        user = None
    else:
        # No encryption for logged in users
        data = e89_security.tools._get_user_data(request, "", False, multipart=False)
        user = e89_syncing.syncing_utils.get_user_object(request.user)
        data["token"] = ""

    if getattr(settings, 'SYNC_DEBUG', False):
        print >>sys.stderr, 'GET DATA FROM SERVER: RECEIVED ' + json.dumps(data, ensure_ascii=False)

    token, timestamp, timestamps = e89_syncing.syncing_utils.extract_meta_data(data)

    if user is None:
        UserModel = apps.get_model(settings.SYNC_USER_MODEL)
        try:
            user = UserModel.objects.get(**{settings.SYNC_TOKEN_ATTR:token,settings.SYNC_TOKEN_ATTR + "__isnull":False})
        except UserModel.DoesNotExist:
            response = DataSyncHelper.getEmptyModifiedDataResponse()
            user = None

    if user is not None:
        if identifier is not None:
            response = DataSyncHelper.getModifiedDataForIdentifier(user = user, parameters = data, identifier = identifier, timestamps = timestamps)
        else:
            assert timestamp is not None or timestamps != {}, "Timestamp was not sent along with data."
            response = DataSyncHelper.getModifiedData(user = user, timestamp = timestamp, timestamps = timestamps)

    if getattr(settings, 'SYNC_DEBUG', False):
        print >>sys.stderr, 'GET DATA FROM SERVER: RESPONDED ' + json.dumps(response, ensure_ascii=False)

    if not request.user.is_authenticated():
        response = e89_security.tools._generate_user_response(response, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False), gzip_active=_is_gzip_active(request))
    else:
        response = e89_security.tools._generate_user_response(response, "", False)

    return response

@csrf_exempt
def send_data_to_server(request):
    if request.method != 'POST':
        return HttpResponse("")

    data = e89_security.tools._get_user_data(request, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False), gzip_active=_is_gzip_active(request))

    if getattr(settings, 'SYNC_DEBUG', False):
        print >>sys.stderr, 'SEND DATA TO SERVER: RECEIVED ' + json.dumps(data, ensure_ascii=False)

    token, timestamp, timestamps = e89_syncing.syncing_utils.extract_meta_data(data)
    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    user = get_object_or_404(UserModel,**{settings.SYNC_TOKEN_ATTR:token})

    assert timestamp is not None or timestamps != {}, "Timestamp was not sent along with data."
    if data.has_key('registration_id'):
        device_id = data['registration_id']
    else:
        device_id = data['device_id']

    response = DataSyncHelper.saveNewData(user = user, timestamp = timestamp, timestamps = timestamps, device_id = device_id, data = data, files = request.FILES)

    if getattr(settings, 'SYNC_DEBUG', False):
        print >>sys.stderr, 'SEND DATA TO SERVER: RESPONDED ' + json.dumps(response, ensure_ascii=False)
    return e89_security.tools._generate_user_response(response, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False), gzip_active=_is_gzip_active(request))

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
        data = e89_security.tools._get_user_data(request, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False), gzip_active=_is_gzip_active(request))

        username = data["username"]
        password = data["password"]

        module_name,class_name = getattr(settings,'SYNC_AUTHENTICATION','e89_syncing.authentication.BaseSyncAuthentication').rsplit('.',1)
        mod = importlib.import_module(module_name)
        SyncAuthentication = getattr(mod, class_name)
        response = SyncAuthentication().authenticate(username,password)

    return e89_security.tools._generate_user_response(response, getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), getattr(settings, "SYNC_ENCRYPTION", False), gzip_active=_is_gzip_active(request))

