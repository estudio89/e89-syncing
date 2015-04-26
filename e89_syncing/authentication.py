# -*- coding: utf-8 -*-
from django.contrib.auth import get_backends
from django.conf import settings
import e89_syncing.syncing_utils

class BaseSyncAuthentication(object):

    def authenticate(self, username, password):
        auth_backend = get_backends()[0]
        user = auth_backend.authenticate(username=username,password=password)
        if not user:
            response = {"verified":False}
        else:
            try:
                response = {"verified":True,"token":e89_syncing.syncing_utils.get_user_token(user, settings.SYNC_TOKEN_ATTR)}
            except AttributeError:
                response = {"verified":False}

        return response
