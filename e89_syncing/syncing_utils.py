from django.utils import timezone
from django.http import Http404
from django.http import HttpResponse
from dateutil import parser
import datetime as dt
import e89_syncing.security
import e89_syncing.RNCryptor
import json

def timestamp_to_datetime(timestamp):
    if timestamp:
        timestamp = parser.parse(timestamp)
    else:
        timestamp = dt.datetime(1, 1, 1)
    return timestamp

def get_new_timestamp():
    new_timestamp = timezone.now()
    return new_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")

def get_user_token(user, attr):
    return reduce(getattr, attr.split('.'), user)

def _get_user_data(request):
    body = request.body
    request._encoding="ISO-8859-1"
    try:
        if request.POST.has_key("json"):
            data = json.loads(e89_syncing.security.decrypt_message(request.POST['json']))
        else:
            data = json.loads(e89_syncing.security.decrypt_message(body))
    except e89_syncing.RNCryptor.BadData:
        raise Http404

    return data

def _generate_user_response(data):
    data = e89_syncing.security.encrypt_message(data)
    return HttpResponse(data,content_type="application/json; charset=ISO-8859-1")