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
import logging

LOGGER = logging.getLogger(__name__)

@csrf_exempt
@e89_security.tools.secure_view(encryption_key=lambda: getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), encryption_active=lambda: getattr(settings, "SYNC_ENCRYPTION", False))
def get_data_from_server(request, data, identifier = None):

    if not request.user.is_authenticated():
        user = None
    else:
        user = e89_syncing.syncing_utils.get_user_object(request.user)
        data["token"] = ""

    if getattr(settings, 'SYNC_DEBUG', False):
        LOGGER.info('GET DATA FROM SERVER: RECEIVED ' + json.dumps(data, ensure_ascii=False))

    token, timestamp, timestamps = e89_syncing.syncing_utils.extract_meta_data(data)
    platform = e89_syncing.syncing_utils.get_platform(request)
    app_version = e89_syncing.syncing_utils.get_app_version(request)

    if user is None:
        user,response = e89_syncing.syncing_utils.get_user_from_token(token)

    if user is not None:
        try:
            if identifier is not None:
                response = DataSyncHelper.getModifiedDataForIdentifier(user = user, parameters = data, identifier = identifier, timestamps = timestamps, platform = platform, app_version = app_version)
            else:
                assert timestamp is not None or timestamps != {}, "Timestamp was not sent along with data."
                response = DataSyncHelper.getModifiedData(user = user, timestamp = timestamp, timestamps = timestamps, platform = platform, app_version = app_version)
        except DataSyncHelper.ExpiredTokenException:
            response = DataSyncHelper.getExpiredTokenResponse()

    if getattr(settings, 'SYNC_DEBUG', False):
        LOGGER.info('GET DATA FROM SERVER: RESPONDED ' + json.dumps(response, ensure_ascii=False))

    return response

@csrf_exempt
@e89_security.tools.secure_view(encryption_key=lambda: getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), encryption_active=lambda: getattr(settings, "SYNC_ENCRYPTION", False))
def send_data_to_server(request, data):

    if getattr(settings, 'SYNC_DEBUG', False):
        LOGGER.info('SEND DATA TO SERVER: RECEIVED ' + json.dumps(data, ensure_ascii=False))

    token, timestamp, timestamps = e89_syncing.syncing_utils.extract_meta_data(data)
    platform = e89_syncing.syncing_utils.get_platform(request)
    app_version = e89_syncing.syncing_utils.get_app_version(request)

    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    user,response = e89_syncing.syncing_utils.get_user_from_token(token)

    if user is not None:
        assert timestamp is not None or timestamps != {}, "Timestamp was not sent along with data."
        if data.has_key('registration_id'):
            device_id = data['registration_id']
        else:
            device_id = data['device_id']

        try:
            response = DataSyncHelper.saveNewData(user = user, timestamp = timestamp, timestamps = timestamps, device_id = device_id, data = data, files = request.FILES, platform = platform, app_version = app_version)
        except DataSyncHelper.ExpiredTokenException:
            response = DataSyncHelper.getExpiredTokenResponse()

    if getattr(settings, 'SYNC_DEBUG', False):
        LOGGER.info('SEND DATA TO SERVER: RESPONDED ' + json.dumps(response, ensure_ascii=False))
    return response

@csrf_exempt
@e89_security.tools.secure_view(encryption_key=lambda: getattr(settings, "SYNC_ENCRYPTION_PASSWORD", ""), encryption_active=lambda: getattr(settings, "SYNC_ENCRYPTION", False))
def authenticate(request, data):
    ''' View para autenticação. Deve receber como parâmetro (via POST), um json no formato:

        {
            "username": "...",
            "senha": "..."
        }

    '''

    response = {}
    if request.method == "POST":

        username = data["username"]
        password = data["password"]

        module_name,class_name = getattr(settings,'SYNC_AUTHENTICATION','e89_syncing.authentication.BaseSyncAuthentication').rsplit('.',1)
        mod = importlib.import_module(module_name)
        SyncAuthentication = getattr(mod, class_name)

        platform = e89_syncing.syncing_utils.get_platform(request)
        app_version = e89_syncing.syncing_utils.get_app_version(request)
        response = SyncAuthentication().authenticate(username,password, platform=platform, app_version=app_version)

    return response

