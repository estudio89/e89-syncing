# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import Http404
from django.db import transaction, OperationalError
from django.apps import apps
from e89_syncing.apps import E89SyncingConfig
from e89_syncing.syncing_utils import *
import time

def saveNewData(user, timestamp, timestamps, device_id, data, files, platform = None, app_version = None):
	''' Percorre todos os SyncManagers solicitando que salvem os dados correspondentes.'''
	response = {}
	new_objects = {}
	for key in data.keys():
		sync_manager = E89SyncingConfig.get_sync_manager(key)
		if sync_manager is not None:
			attempts = 0
			while attempts < 3:
				try:
					with transaction.atomic():
						manager_response,objects = sync_manager.saveNewData(user = user, device_id = device_id, data = data[key], files = files, platform = platform, app_version = app_version)
						break
				except OperationalError as e:
					attempts += 1
					time.sleep(0.2)
					if attempts == 3:
						raise e

			with transaction.atomic():
				response.update(manager_response)
				new_objects[sync_manager.getIdentifier()] = [o.id for o in objects if o is not None]

	new_data = getModifiedData(user = user, timestamp = timestamp, timestamps = timestamps, exclude = new_objects, platform = platform, app_version = app_version)
	response.update(new_data)

	return response

def getModifiedData(user, timestamps, timestamp = None, exclude = {}, platform = None, app_version = None):
	''' Percorre todos os SyncManagers solicitando que retornem quaisquer dados a serem
		enviados ao client correspondente. O parâmetro exclude é um dicionário
		de listas contendo ids que não devem ser buscados não query. Ex:

		exclude = {
					"identifier1":[1,2,3],
					"identifier2":[1,2],
					...
				  }
		'''
	data = {"timestamps":{}}
	coupled_sync_managers = []
	for sync_manager in E89SyncingConfig.get_sync_managers():
		identifier = sync_manager.getIdentifier()
		coupled = E89SyncingConfig.get_coupled_sync_managers(identifier)
		if timestamps:
			timestamp = timestamps.get(identifier, None)
			if timestamp is None and identifier not in coupled_sync_managers:
				continue
			else:
				# coupled sync managers can send data in the same request
				for sm in coupled: coupled_sync_managers.append(sm)

		timestamp = timestamp_to_datetime(timestamp)
		manager_data,manager_parameters = sync_manager.getModifiedData(user = user, timestamp = timestamp, exclude = exclude.get(identifier,[]), platform = platform, app_version = app_version)
		manager_parameters['data'] = manager_data
		data[identifier] = manager_parameters
		new_timestamp = get_new_timestamp()
		data["timestamps"][identifier] = new_timestamp

		# Synchronizing timestamps across coupled sync managers
		for sm in coupled: data["timestamps"][sm] = new_timestamp
	SyncLog = apps.get_model('e89_syncing','SyncLog')
	SyncLog.objects.store_timestamps(user, data["timestamps"])

	data["timestamp"] = get_new_timestamp() # Only to maintain compatibility
	return data

def getExpiredTokenResponse():
	''' Returns an empty response to all sync managers. Used when replying to a user that
		is not allowed to access data.'''

	data = {}
	for sync_manager in E89SyncingConfig.get_sync_managers():
		identifier = sync_manager.getIdentifier()
		data[identifier] = {'data':[]}

	expirable_token = getattr(settings, 'SYNC_EXPIRABLE_TOKEN', False)
	if expirable_token:
		data['expiredToken'] = {'data': [], 'expiredToken':True}
	else:
		data['logout'] = {'data':[],'logout':True}

	data["timestamp"] = get_new_timestamp() # Only to maintain compatibility
	data["timestamps"] = {}

	return data

def getModifiedDataForIdentifier(user, parameters, identifier, timestamps, platform = None, app_version = None):
	''' Busca dados especificamente para um identifier. Utilizado por clientes que
		implementam cache parcial. '''

	sync_manager = E89SyncingConfig.get_sync_manager(identifier)
	if sync_manager is None:
		raise Http404
	timestamp = timestamps.get(sync_manager.getIdentifier(), "")
	manager_data,manager_parameters = sync_manager.getModifiedData(user = user, timestamp = timestamp_to_datetime(timestamp), parameters = parameters, platform = platform, app_version = app_version)
	manager_parameters['data'] = manager_data

	data = {identifier:manager_parameters}
	if timestamps.has_key(identifier): # Not paginating, but updating
		coupled = E89SyncingConfig.get_coupled_sync_managers(identifier)
		if not coupled:
			data["timestamps"] = {identifier:get_new_timestamp()}
		else:
			data["timestamps"] = {}
			for sm in coupled:
				coupled_sync_manager = E89SyncingConfig.get_sync_manager(sm)
				coupled_data,coupled_parameters = coupled_sync_manager.getModifiedData(user = user, timestamp = timestamp_to_datetime(timestamp), parameters = parameters, platform = platform, app_version = app_version)
				coupled_parameters['data'] = coupled_data
				data[sm] = coupled_parameters
				new_timestamp = get_new_timestamp()
				data["timestamps"][identifier] = new_timestamp
				data["timestamps"][sm] = new_timestamp

		SyncLog = apps.get_model('e89_syncing','SyncLog')
		SyncLog.objects.store_timestamps(user, data["timestamps"])
	return data



class BaseSyncManager(object):

	def getIdentifier(self):
		''' Retorna um identificador utilizado na comunicação JSON.
			Por exemplo, se o identificador for "teste", ao enviar dados ao client,
			o JSON criado será:
			{
				...
				"teste": [obj1, obj2, ...],
				...
			}

			'''
		pass

	def getResponseIdentifier(self):
		''' Deve retornar um identificador para a resposta de recebimento de dados
			do client. Para'''
		pass

	def getModifiedData(self, user, timestamp, parameters = None, exclude = [], platform = None, app_version = None):
		''' Searches for new data to be sent. Must return a list of serialized items and a dictionary
			containing parameters that should be passed back to the client.
			The exclude parameter is a list of object ids that must not be considered in the query.'''
		pass

	def saveNewData(self, user, device_id, data, files = None, platform = None, app_version = None):
		''' Saves new data received. Must return 2 objects:
			1. A dictionary that contains a list with data to be sent in response.
			   The key in the dictionary MUST be equal to the response identifier.
				For instance:
					{
						"news_id":[
							{"id":2,"id_client":1},
							...
						]
					}
			2. List with all the objects that were created
			'''

		response = []
		new_objects = []
		for object in data:
			object_response, new_object = self.saveObject(user = user, device_id = device_id, object = object, files = files, platform = platform, app_version = app_version)
			response.append(object_response)
			new_objects.append(new_object)

		return {self.getResponseIdentifier():response},new_objects

	def saveObject(self, user, device_id, object, files = None, platform = None, app_version = None):
		''' Saves an object in the database. Must return 2 objects:
			1. A dictionary containing data to be sent in response to the client.
			For example: {"id":1,"id_client":3}.
			2. The object that was saved in the database.'''

		pass

	def serializeObject(self, object):
		''' This method is responsible for transforming an object into a dictionary
			that will be converted to json later. It must return a dictionary. '''
		pass

class ExpiredTokenException(Exception):
	pass

