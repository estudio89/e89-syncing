1. Adicionar 'e89_syncing' ao arquivo settings.py nos INSTALLED_APPS.

2. Para cada model que necessitar de sincronização, implementar uma classe que herda da classe BaseSyncManager.

3. No arquivo settings.py, incluir setting SYNC_MANAGERS que é uma lista de strings indicando a classe que corresponde a cada SyncManager.
   Por exemplo:

	SYNC_MANAGERS = ['formularios.sync_managers.SyncManagerRegistro', ...]

	Incluir também o caminho até o atributo token do usuário na opção SYNC_TOKEN_ATTR. Por exemplo, se para buscar o token do usuário, é preciso do seguinte:

		token = user.userprofissional.token

	então SYNC_TOKEN_ATTR deverá ser:

		SYNC_TOKEN_ATTR = "userprofissional.token"

	Caso se deseje utilizar criptografia em toda a comunicação, definir ainda as opções:

		SYNC_ENCRYPTION = True

		SYNC_ENCRYPTION_PASSWORD = "password"

4. Incluir url's no arquivo urls.py do projeto:

	url(r'syncing/', include('e89_syncing.urls')),

5. Considerando a configuração do item 4, serão criadas as seguintes url's:

	/syncing/get-data-from-server/ >> Retorna novos dados do servidor baseado no timestamp
	/syncing/get-data-from-server/<model_identifier>/ >> Retorna dados específicos de um model (cache parcial)
	/syncing/send-data-to-server/ >> Recebimento de dados de um client