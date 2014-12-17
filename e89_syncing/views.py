# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.contrib.auth import get_backends
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


import e89_syncing.syncing_utils
import DataSyncHelper
import json
import sys

@csrf_exempt
def get_data_from_server(request, identifier = None):
    if request.method != 'POST':
        return HttpResponse("")

    try:
        data = json.loads(request.body)
    except ValueError:
        data = json.loads(request.POST['json'])
    print >>sys.stderr, 'GET DATA FROM SERVER: RECEIVED ' + str(data)
    token = data["token"]

    if identifier is not None:
        response = DataSyncHelper.getModifiedDataForIdentifier(token = token, parameters = data, identifier = identifier)
    else:
        timestamp = data["timestamp"]
        response = DataSyncHelper.getModifiedData(token = token, timestamp = timestamp)
    print >>sys.stderr, 'GET DATA FROM SERVER: RESPONDED ' + str(response)
    return HttpResponse(json.dumps(response,ensure_ascii=False),content_type="application/json; charset=utf-8")

@csrf_exempt
def send_data_to_server(request):
    if request.method != 'POST':
        return HttpResponse("")

    try:
        body = request.body
        data = json.loads(body)
    except ValueError:
        data = json.loads(request.POST['json'])

    print >>sys.stderr, 'SEND DATA TO SERVER: RECEIVED ' + str(data)
    token = data["token"]
    timestamp = data["timestamp"]
    if data.has_key('registration_id'):
        device_id = data['registration_id']
    else:
        device_id = data['device_id']

    response = DataSyncHelper.saveNewData(token = token, timestamp = timestamp, device_id = device_id, data = data, files = request.FILES)

    print >>sys.stderr, 'SEND DATA TO SERVER: RESPONDED ' + str(response)
    return HttpResponse(json.dumps(response,ensure_ascii=False),content_type="application/json; charset=utf-8")

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
        try:
            data = json.loads(request.body)
        except ValueError:
            data = json.loads(request.POST['json'])
        username = data["username"]
        password = data["password"]
        auth_backend = get_backends()[0]
        user = auth_backend.authenticate(username=username,password=password)
        if not user:
            response = {"verified":False}
        else:
            if not user.is_profissional():
                response = {"verified":False}
            else:
                try:
                    response = {"verified":True,"token":e89_syncing.syncing_utils.get_user_token(user, settings.SYNC_TOKEN_ATTR)}
                except AttributeError:
                    response = {"verified":False}

    return HttpResponse(json.dumps(response,ensure_ascii=False),content_type="application/json; charset=utf-8")