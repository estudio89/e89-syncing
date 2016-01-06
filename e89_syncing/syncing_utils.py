from django.utils import timezone
from django.http import Http404
from django.http import HttpResponse
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from dateutil import parser
import datetime as dt
import json

FIRST_TIMESTAMP = timezone.now().replace(day=1,year=1900,month=1,minute=0,hour=0,second=0,microsecond=0)
def timestamp_to_datetime(timestamp):
    if isinstance(timestamp, dt.datetime):
        return timestamp

    if timestamp:
        timestamp = parser.parse(timestamp)
    else:
        timestamp = FIRST_TIMESTAMP
    return timestamp

def datetime_to_timestamp(date):
    return date.strftime("%Y-%m-%d %H:%M:%S.%f %Z")

def get_new_timestamp():
    new_timestamp = timezone.now()
    return datetime_to_timestamp(new_timestamp)

def get_user_token(user, attr):
    return reduce(getattr, attr.split('.'), user)

def get_user_id(user, attr):
    if attr is None:
        attr = 'id'

    return get_user_token(user, attr)


def extract_meta_data(data):
    token = data.pop("token")
    timestamp = data.pop("timestamp","") # maintains compatibility
    timestamps = data.pop("timestamps",{})
    return token, timestamp, timestamps

def get_platform(request):
    return request.META.get('HTTP_X_E89_SYNCING_PLATFORM')

def get_app_version(request):
    return request.META.get('HTTP_X_APP_VERSION')

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

def get_user_from_token(token):
    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    response = None
    try:
        user = UserModel.objects.get(**{settings.SYNC_TOKEN_ATTR:token,settings.SYNC_TOKEN_ATTR + "__isnull":False})
    except UserModel.DoesNotExist:
        import DataSyncHelper
        response = DataSyncHelper.getExpiredTokenResponse()
        user = None
    return user,response

def check_performance(user, timestamps={}, print_results=True):
    ''' Use this to check the number of queries run in order to fetch data for each sync manager as well as the time taken. '''

    from django.db import connection
    import time
    from e89_syncing.apps import E89SyncingConfig

    result = {}
    initial_query_count = len(connection.queries)
    initial_time = time.time()
    for sync_manager in E89SyncingConfig.get_sync_managers():
        identifier = sync_manager.getIdentifier()
        queries_bf = len(connection.queries)
        timestamp = timestamps.get(identifier, FIRST_TIMESTAMP)
        time_bf = time.time()
        manager_data,manager_parameters = sync_manager.getModifiedData(user = user, timestamp = timestamp)
        time_taken = time.time() - time_bf
        queries_performed = len(connection.queries) - queries_bf
        result[identifier] = {
            "queries_count":queries_performed,
            "time_taken":time_taken,
            "queries": connection.queries[queries_bf::]
        }
    total_queries = len(connection.queries) - initial_query_count
    if print_results:
        print "TOTAL NUMBER OF QUERIES:",total_queries
        print "TOTAL TIME (s):", time.time() - initial_time
        print "SLOWEST:",max(result.items(),key=lambda item:item[1]["time_taken"])[0]
        print
        print "identifier, time_taken","queries_count"
        for sm in result.keys(): print sm,result[sm]["time_taken"],result[sm]["queries_count"]

    return result
