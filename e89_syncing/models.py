# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
import e89_syncing.syncing_utils
import json


class SyncLogManager(models.Manager):

	def get_timestamps(self, user):
		sl_list = self.filter(user=user)
		timestamps = {}
		for sl in sl_list:
			timestamps[sl.identifier] = sl.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")

		return timestamps

	def store_timestamps(self, user, timestamps):
		for identifier,timestamp in timestamps.items():
			timestamp = e89_syncing.syncing_utils.timestamp_to_datetime(timestamp)
			self.update_or_create(user=user, identifier=identifier, defaults={"timestamp":timestamp})

class SyncLog(models.Model):
	user = models.ForeignKey(settings.SYNC_USER_MODEL)
	timestamp = models.DateTimeField()
	identifier = models.CharField(max_length=100)

	objects = SyncLogManager()