# -*- coding: utf-8 -*-
from django.contrib.auth import get_backends
from django.conf import settings
from django.apps import apps
import e89_syncing.syncing_utils


class BaseSyncAuthentication(object):

    def authenticate(self, username, password, platform, app_version):
        auth_backend = get_backends()[0]
        user = auth_backend.authenticate(username=username,password=password, platform=platform, app_version=app_version)

        if not user:
            response = {"verified":False}
        else:
            user = e89_syncing.syncing_utils.get_user_object(user)
            try:
                response = {"verified":True,"token":e89_syncing.syncing_utils.get_user_token(user, settings.SYNC_TOKEN_ATTR), "id": e89_syncing.syncing_utils.get_user_id(user, getattr(settings,"SYNC_ID_ATTR",None))}
            except AttributeError:
                response = {"verified":False}

        return response
