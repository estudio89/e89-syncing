from django.utils import timezone
from django.http import Http404
from django.http import HttpResponse
from django.apps import apps
from django.conf import settings
from dateutil import parser
import datetime as dt
import json

FIRST_TIMESTAMP = dt.datetime(1, 1, 1)
def timestamp_to_datetime(timestamp):
    if isinstance(timestamp, dt.datetime):
        return timestamp

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

def extract_meta_data(data):
    token = data.pop("token")
    timestamp = data.pop("timestamp","") # maintains compatibility
    timestamps = data.pop("timestamps",{})
    return token, timestamp, timestamps

def get_user_object(user):
    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    if user._meta.model == UserModel:
        return user

    related = user._meta.get_all_related_objects()
    for rel in related:
        if rel.related_model == UserModel:
            related_attr = rel.get_accessor_name()
            return getattr(user, related_attr)
    raise ValueError("The user object returned by the authentication backend is from the model %s when it should be %s"%(user._meta.model_name, UserModel._meta.model_name))
