from django.apps import AppConfig
from django.conf import settings
from collections import OrderedDict
import importlib

class E89SyncingConfig(AppConfig):
	sync_managers = OrderedDict()
	name='e89_syncing'

	def ready(self):

		# Initializing sync managers
		for module_name in settings.SYNC_MANAGERS:
			module_name,class_name = module_name.rsplit('.',1)
			mod = importlib.import_module(module_name)
			sync_manager_class = getattr(mod, class_name)
			sync_manager = sync_manager_class()
			E89SyncingConfig.sync_managers[sync_manager.getIdentifier()] = {"manager": sync_manager, "coupled":[]}

		# Identifying coupled sync managers
		identifiers = E89SyncingConfig.sync_managers.keys()
		for identifier in identifiers:
			for coupled in identifiers:
				if identifier == coupled:
					continue

				if identifier in coupled or coupled in identifier:
					E89SyncingConfig.sync_managers[identifier]["coupled"].append(coupled)

	@staticmethod
	def get_sync_managers():
		return [value["manager"] for value in E89SyncingConfig.sync_managers.values()]

	@staticmethod
	def get_coupled_sync_managers(identifier):
		return E89SyncingConfig.sync_managers[identifier]["coupled"]

	@staticmethod
	def get_sync_manager(identifier):
		value = E89SyncingConfig.sync_managers.get(identifier)
		if value:
			return value["manager"]
		return



