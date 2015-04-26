# -*- coding: utf-8 -*-
from django.conf import settings
from django.http import Http404
from django.db import transaction

from e89_syncing.apps import E89SyncingConfig
from e89_syncing.syncing_utils import *

def saveNewData(token, timestamp, device_id, data, files):
	''' Percorre todos os SyncManagers solicitando que salvem os dados correspondentes.'''
	with transaction.atomic():
		response = {}
		new_objects = {}
		for key in data.keys():
			sync_manager = E89SyncingConfig.get_sync_manager(key)
			if sync_manager is not None:
				manager_response,objects = sync_manager.saveNewData(token = token, device_id = device_id, data = data[key], files = files)
				response.update(manager_response)
				new_objects[sync_manager.getIdentifier()] = [o.id for o in objects]

	new_data = getModifiedData(token = token, timestamp = timestamp, exclude = new_objects)
	response.update(new_data)

	return response

def getModifiedData(token, timestamp, exclude = {}):
	''' Percorre todos os SyncManagers solicitando que retornem quaisquer dados a serem
		enviados ao client correspondente. O parâmetro exclude é um dicionário
		de listas contendo ids que não devem ser buscados não query. Ex:

		exclude = {
					"identifier1":[1,2,3],
					"identifier2":[1,2],
					...
				  }
		'''

	timestamp = timestamp_to_datetime(timestamp)
	data = {}
	for sync_manager in E89SyncingConfig.get_sync_managers():
		identifier = sync_manager.getIdentifier()
		manager_data,manager_parameters = sync_manager.getModifiedData(token = token, timestamp = timestamp, exclude = exclude.get(identifier,[]))
		manager_parameters['data'] = manager_data
		data[identifier] = manager_parameters

	data["timestamp"] = get_new_timestamp()
	return data

def getModifiedDataForIdentifier(token, parameters, identifier):
	''' Busca dados especificamente para um identifier. Utilizado por clientes que
		implementam cache parcial. '''

	sync_manager = E89SyncingConfig.get_sync_manager(identifier)
	if sync_manager is None:
		raise Http404
	manager_data,manager_parameters = sync_manager.getModifiedData(token = token, timestamp = timestamp_to_datetime(""), parameters = parameters)
	manager_parameters['data'] = manager_data
	return {sync_manager.getIdentifier():manager_parameters}



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

	def getModifiedData(self, token, timestamp, parameters = None, exclude = []):
		''' Busca dados novos a serem enviados. Deve retornar uma lista de objetos serializados e
			um dicionário com parâmetros a serem repassados ao cliente.
			O parâmetro exclude é uma lista de ids de objetos que devem ser desconsiderados na query.'''
		pass

	def saveNewData(self, token, device_id, data, files = None):
		''' Salva novos dados recebidos. Deve retornar 2 objetos:
			1. Um dicionário que contém uma
				lista com dados a serem enviados em resposta. O key do dicionário DEVE ser
				igual ao ResponseIdentifier. Exemplo:
					{
						"registros_id":[
							{"id":2,"id_client":1},
							...
						]
					}
			2. Lista com todos os objetos criados
			'''

		response = []
		new_objects = []
		for object in data:
			object_response, new_object = self.saveObject(token = token, device_id = device_id, object = object, files = files)
			response.append(object_response)
			new_objects.append(new_object)

		return {self.getResponseIdentifier():response},new_objects

	def saveObject(self, token, device_id, object, files = None):
		''' Salva um objeto no banco. Deve retornar 2 objetos:
			1. Um dicionário contendo dados a serem
			enviados como resposta ao client. Por exemplo: {"id":1,"id_client":3}.
			2. O objeto que foi salvo no banco

			Para objetos compostos, pode ser utilizada uma lógica diferente aqui, mas nesse caso
			o método saveNewData deverá ser reimplementado.'''

		pass

	def serializeObject(self, object):
		''' Método responsável por transformar um objeto em um dicionário a ser
			convertido posteriormente em um JSON. Deve retornar um dicionário. '''
		pass