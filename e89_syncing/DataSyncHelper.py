# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import Http404
from django.db import transaction, OperationalError, IntegrityError
from django.apps import apps
from django.shortcuts import get_object_or_404
from django.core.exceptions import FieldDoesNotExist
from e89_syncing.apps import E89SyncingConfig
from e89_syncing.syncing_utils import *
from e89_tools.tools import camelcase_underscore
import time
from rest_framework.exceptions import ValidationError

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
		if hasattr(self, "identifier"):
			return self.identifier
		else:
			raise NotImplementedError

	def getResponseIdentifier(self):
		''' Deve retornar um identificador para a resposta de recebimento de dados
			do client. Para'''
		if hasattr(self, "response_identifier"):
			return self.response_identifier
		else:
			raise NotImplementedError

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

	def check_has_field(self, Model, field_name):
		try:
			field = Model._meta.get_field(field_name)
			return True
		except FieldDoesNotExist:
			return False

class AbstractSyncManager(BaseSyncManager):
	app_model = ''
	page_size = 10
	serializer = None
	serializer_context_user_key = None
	prefetch_params = []
	allow_creation = False
	pagination_parameter = "max_date"
	extra_serializer_kwargs = {}

	def getModifiedData(self, user, timestamp, parameters = None, exclude = [], platform = None, app_version = None):
		''' Searches for new data to be sent. Must return a list of serialized items and a dictionary
			containing parameters that should be passed back to the client.
			The exclude parameter is a list of object ids that must not be considered in the query.'''

		# Total of 8 queries
		is_paginating_or_first_fetch = self._check_is_paginating(parameters) or timestamp == FIRST_TIMESTAMP
		if parameters is None:
			parameters = {}
		merged_exclude = set(exclude + parameters.pop('exclude',[]))

		# Loading models and getting user
		Model = apps.get_model(self.app_model)

		# Fetching objects and paginating
		objects = Model.objects.get_sync_items(user=user,timestamp=timestamp, **parameters).prefetch_related(*self.prefetch_params).exclude(id__in=merged_exclude)
		response_parameters = {}
		if self.page_size is not None:
			response_parameters = self._get_pagination_response_parameters(objects, timestamp, parameters, is_paginating_or_first_fetch)

		if self.page_size is not None:
			objects = objects[:self.page_size]

		# Serialization
		user_key = self.serializer_context_user_key if self.serializer_context_user_key else "user"
		extra_serializer_kwargs = self.extra_serializer_kwargs or {}
		s = self.serializer(list(objects), context={user_key:user, 'timestamp': timestamp, 'platform': platform, 'app_version': app_version}, many=True, **extra_serializer_kwargs)
		serialized = s.data
		return serialized, response_parameters

	def getExtraSerializerKwargs(self):
		return {}

	def _get_number_new_items(self, objects, timestamp, is_paginating_or_first_fetch):
		return len(objects) if type(objects) == type([]) else objects.count()

	def _get_pagination_response_parameters(self, objects, timestamp, request_params, is_paginating_or_first_fetch):
		''' Returns the pagination parameters necessary for the client to know what to do.
			It checks to see if there are more items in the server than the ones being sent
			and checks if there is a gap between the data the user has and what is in the server,
			in which case the client must delete all its cached items.'''

		response_parameters = {}
		number_items = self._get_number_new_items(objects, timestamp, is_paginating_or_first_fetch)
		if is_paginating_or_first_fetch:
			response_parameters['more'] = self.page_size < number_items
		else:
			response_parameters['deleteCache'] = number_items > self.page_size
			if response_parameters['deleteCache']:
				response_parameters['more'] = True
		return response_parameters

	def _check_is_paginating(self, parameters):
		return parameters is not None and parameters.has_key(self.pagination_parameter)

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
			try:
				object_response, new_object = self.saveObject(user = user, device_id = device_id, object = object, files = files, platform = platform, app_version = app_version)
				response.append(object_response)
				new_objects.append(new_object)
			except Http404:
				self.handleObjectNotFound(user = user, device_id = device_id, object = object, files = files, platform = platform, app_version = app_version)

		return {self.getResponseIdentifier():response},new_objects

	def isAllowed(self, user, device_id, object, files = None, platform = None, app_version = None):
		''' Returns True if the object can be created/updated or False otherwise.'''
		return True

	def saveObject(self, user, device_id, object, files = None, platform = None, app_version = None):
		''' Saves an object in the database. Must return 2 objects:
			1. A dictionary containing data to be sent in response to the client.
			For example: {"id":1,"id_client":3}.
			2. The object that was saved in the database.'''

		if not self.isAllowed(user=user, device_id=device_id, object=object, files=files, platform=platform, app_version=app_version):
			return {"idClient": object.get("idClient"), "id":-1}, None

		Model = apps.get_model(self.app_model)
		device_id = object.get("deviceId", device_id)
		if self.check_has_field(Model, 'idClient') and object.has_key("idClient") and device_id is not None and Model.objects.filter(idClient=object['idClient'], deviceId=device_id).exists():
			instance = Model.objects.filter(idClient=object['idClient'], deviceId=device_id).first()
		elif object.has_key("id"):
			instance = get_object_or_404(Model,id=object['id'])
		elif self.allow_creation:
			instance = None # Creating object
		else:
			raise Http404
		user_key = self.serializer_context_user_key if self.serializer_context_user_key else "user"

		if instance is None and self.check_has_field(Model, 'deviceId'):
			object['deviceId'] = device_id

		extra_serializer_kwargs = self.extra_serializer_kwargs or {}
		s = self.serializer(instance, data=object, context={user_key:user,'device_id':device_id, 'files':files}, **extra_serializer_kwargs)
		try:
			s.is_valid(raise_exception=True)
			saved_obj = s.save(**object)
		except ValidationError, e:
			if self.allow_creation and s._errors.has_key("non_field_errors"):
				try:
					saved_obj = Model.objects.get(idClient=object["idClient"], deviceId=device_id)
				except Model.DoesNotExist:
					raise e
			else:
				raise e
		except IntegrityError, e:
			try:
				saved_obj = Model.objects.get(idClient=object["idClient"], deviceId=device_id)
			except Model.DoesNotExist:
				raise e


		return {"id":saved_obj.id, "idClient":object.get("idClient", None)},saved_obj


	def serializeObject(self, object):
		''' This method is responsible for transforming an object into a dictionary
			that will be converted to json later. It must return a dictionary. '''

		return {}

	def handleObjectNotFound(self, user, device_id, object, files = None, platform = None, app_version = None):
		raise Http404

class ObjectDeletedSyncManager(BaseSyncManager):
	app_model = ''
	owner_attr = None

	def getModifiedData(self, user, timestamp, parameters = None, exclude = [], platform = None, app_version = None):
		''' Searches for new data to be sent. Must return a list of serialized items and a dictionary
			containing parameters that should be passed back to the client.
			The exclude parameter is a list of object ids that must not be considered in the query.'''

		# Loading models and getting employee
		employee = user
		try:
			ModelDeleted = apps.get_model(self.app_model + 'Deleted')
		except LookupError:
			ModelDeleted = None
		ModelToDelete = apps.get_model(self.app_model + 'ToDelete')
		fk_attr = camelcase_underscore(self.app_model.split('.')[1]) + '_id'

		if timestamp == FIRST_TIMESTAMP: # First fetch
			deleted = []
		else:
			owner_attr = self.owner_attr if self.owner_attr else "user"
			owner_attr += "_id"
			fargs = {"timestamp__gt": timestamp}
			if self.check_has_field(ModelToDelete, owner_attr):
				fargs[owner_attr] = employee.id
			deleted = list(ModelToDelete.objects.filter(**fargs).values(fk_attr))
			if ModelDeleted:
				deleted += list(ModelDeleted.objects.filter(timestamp__gt=timestamp).values(fk_attr))
			attr = camelcase_underscore(self.app_model.split('.')[1]) + '_id'
			deleted = {v[attr]:v for v in deleted}.values()

		response_parameters = {}
		return deleted, response_parameters

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

		return {},[]

	def saveObject(self, user, device_id, object, files = None, platform = None, app_version = None):
		''' Saves an object in the database. Must return 2 objects:
			1. A dictionary containing data to be sent in response to the client.
			For example: {"id":1,"id_client":3}.
			2. The object that was saved in the database.'''

		return {},None


	def serializeObject(self, object):
		''' This method is responsible for transforming an object into a dictionary
			that will be converted to json later. It must return a dictionary. '''
		return {}

class ExpiredTokenException(Exception):
	pass

