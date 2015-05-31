from django.utils import timezone
from django.http import Http404
from django.http import HttpResponse
from dateutil import parser
import datetime as dt
import json

FIRST_TIMESTAMP = dt.datetime(1, 1, 1)
def timestamp_to_datetime(timestamp):
    if timestamp:
        timestamp = parser.parse(timestamp)
    else:
        timestamp = FIRST_TIMESTAMP
    return timestamp

def get_new_timestamp():
    new_timestamp = timezone.now()
    return new_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")

def get_user_token(user, attr):
    return reduce(getattr, attr.split('.'), user)