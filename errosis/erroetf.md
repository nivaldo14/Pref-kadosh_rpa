UnicodeDecodeError
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe3 in position 96: invalid continuation byte

Traceback (most recent call last)
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\flask\app.py", line 1536, in __call__
return self.wsgi_app(environ, start_response)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\flask\app.py", line 1514, in wsgi_app
response = self.handle_exception(e)
           ^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\flask\app.py", line 1511, in wsgi_app
response = self.full_dispatch_request()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\flask\app.py", line 919, in full_dispatch_request
rv = self.handle_user_exception(e)
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\flask\app.py", line 917, in full_dispatch_request
rv = self.dispatch_request()
     ^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\flask\app.py", line 902, in dispatch_request
return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\app.py", line 207, in login
user = Usuario.query.filter_by(username=username).first()
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\query.py", line 2759, in first
return self.limit(1)._iter().first()  # type: ignore
       ^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\query.py", line 2857, in _iter
result: Union[ScalarResult[_T], Result[_T]] = self.session.execute(
                                              
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2351, in execute
return self._execute_internal(
       
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2239, in _execute_internal
conn = self._connection_for_bind(bind)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\session.py", line 2108, in _connection_for_bind
return trans._connection_for_bind(engine, execution_options)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "<string>", line 2, in _connection_for_bind
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\state_changes.py", line 137, in _go
ret_value = fn(self, *arg, **kw)
            ^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\orm\session.py", line 1187, in _connection_for_bind
conn = bind.connect()
       ^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\engine\base.py", line 3285, in connect
return self._connection_cls(self)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\engine\base.py", line 143, in __init__
self._dbapi_connection = engine.raw_connection()
                         ^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\engine\base.py", line 3309, in raw_connection
return self.pool.connect()
       ^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 447, in connect
return _ConnectionFairy._checkout(self)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 1264, in _checkout
fairy = _ConnectionRecord.checkout(pool)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 711, in checkout
rec = pool._do_get()
      ^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\impl.py", line 177, in _do_get
with util.safe_reraise():
^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 224, in __exit__
raise exc_value.with_traceback(exc_tb)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\impl.py", line 175, in _do_get
return self._create_connection()
       ^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 388, in _create_connection
return _ConnectionRecord(self)
       ^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 673, in __init__
self.__connect()
^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 899, in __connect
with util.safe_reraise():
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\util\langhelpers.py", line 224, in __exit__
raise exc_value.with_traceback(exc_tb)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\pool\base.py", line 895, in __connect
self.dbapi_connection = connection = pool._invoke_creator(self)
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\engine\create.py", line 661, in connect
return dialect.connect(*cargs, **cparams)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\sqlalchemy\engine\default.py", line 630, in connect
return self.loaded_dbapi.connect(*cargs, **cparams)  # type: ignore[no-any-return]  # NOQA: E501
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "C:\Users\Nivaldo\Desktop\Desenvolvimento\2026\transpGaucho\kadoshBot\front_postgres\.venv\Lib\site-packages\psycopg2\__init__.py", line 135, in connect
conn = _connect(dsn, connection_factory=connection_factory, **kwasync)
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe3 in position 96: invalid continuation byte