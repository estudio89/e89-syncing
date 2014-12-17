from django.utils import timezone
from dateutil import parser
import datetime as dt

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