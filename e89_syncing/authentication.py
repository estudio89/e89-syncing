# -*- coding: utf-8 -*-
from django.contrib.auth import get_backends
from django.conf import settings
from django.apps import apps
import e89_syncing.syncing_utils


def get_user_object(user):
    UserModel = apps.get_model(settings.SYNC_USER_MODEL)
    if user._meta.model == UserModel:
        return user

    related = user._meta.get_all_related_objects()
    for rel in related:
        if rel.related_model == UserModel:
            related_attr = rel.get_accessor_name()
            return getattr(user, related_attr)
    raise ValueError("The user object returned by the authentication backend if from the model %s when it should be %s"%(user._meta.model_name, UserModel._meta.model_name))

class BaseSyncAuthentication(object):

    def authenticate(self, username, password):
        auth_backend = get_backends()[0]
        user = auth_backend.authenticate(username=username,password=password)

        if not user:
            response = {"verified":False}
        else:
            user = get_user_object(user)
            try:
                response = {"verified":True,"token":e89_syncing.syncing_utils.get_user_token(user, settings.SYNC_TOKEN_ATTR)}
            except AttributeError:
                response = {"verified":False}

        return response
