======================================
Using figenv for configuration objects
======================================

``figenv`` provides a metaclass that makes smart decisions about variables to
cast them to the correct type when they are accessed on a configuration object.
It is a drop-in replacement for libraries like ``Flask-Env``, but instead of
setting the attributes at import time, the values are pulled from the
environment at access time, allowing for patching multiple attributes in the
test suite with one ``patch.dict()`` request to ``os.environ``.

``figenv`` also allows for setting attributes as functions, so that the user can
take values that are broken up into multiple parts and construct them into a
single value.

You do not need to instantiate the Config class with the :py:class:`figenv.MetaConfig` object
because the attributes are set by the metaclass and are all classmethods.

Lets say you have the following

.. code-block:: python

    class Config:
        DATABASE_URL = 'postgresql://username:password@localhost:5432/dbname'

This parameter can be converted to be able to be constructed from a list of attributes.

.. code-block:: python

    class Config(metaclass=figenv.MetaConfig):
        POSTGRES_MAIN_HOST = 'localhost'
        POSTGRES_MAIN_DATABASE = 'dbname'
        POSTGRES_MAIN_PASSWORD = 'password'
        POSTGRES_MAIN_USER = 'username'
        POSTGRES_MAIN_PORT = 5432

    	def DATABASE_URL(cls):
            return 'postgresql://{user}:{password}@{host}:{port}/{db}?sslmode=prefer'.format(
                user=cls.POSTGRES_MAIN_USER,
                password=cls.POSTGRES_MAIN_PASSWORD,
                host=cls.POSTGRES_MAIN_HOST,
                port=cls.POSTGRES_MAIN_PORT,
                db=cls.POSTGRES_MAIN_DATABASE,
            )

Now, if ``Config.DATABASE_URL`` is requested, first the figenv metaclass functions
will check the ``DATABASE_URL`` environment variable, and then if it is not set, it
will call the function.

Patching figenv for tests
=========================

Because figenv depends heavily on the environment, even if you patch the Config
object directly, environment variables in the test suite can overwrite those
patches. Instead you should patch the environment.

.. note:: It is not possible to directly edit the attributes, they are treated as defaults.

.. code-block:: python

    >>> import figenv, os, unittest.mock
    >>> class Config(metaclass=figenv.MetaConfig):
    ...   FOO = 'bar'
    ...
    >>> assert Config.FOO == 'bar'
    >>> with unittest.mock.patch.dict(os.environ, {'FOO': 'baz'}):
    ...     assert Config.FOO == 'baz'
    ...
    >>>

When the ``patch.dict`` context manager is exited, the ``os.environ`` dictionary is
reverted back to what it was previously.

Extra stuff figenv can do
=========================

Creating strict functions
-------------------------

If there is a function that should not be overwritable by the environment
variables, there is decorator :py:func:`figenv.strict` which can be added to the
function, and this will make sure it is called, and not overwritten by
environment variables.

.. code-block:: python

    import os
    import platform
    from unittest.mock import patch

    import figenv

    class Config(metaclass=figenv.MetaConfig):

        @figenv.strict
        def HOSTNAME(cls):
            return platform.node()

    with patch.dict(os.environ, {'HOSTNAME': 'myfakehost'}):
        assert Config.HOSTNAME == platform.node()

Coercion
--------

This feature allows ``figenv`` to convert strings from environment variables to
appropriate python objects automatically. Here are a list of the coercion that
``figenv`` handles by default:

- Any capitalization of strings true or false  in the environment variable will
  be turned into the the ``True`` or ``False`` boolean value.
- Anything with all digits in it and only one period will be turned into a float
- Anything that is all digits will be turned into an int
- You can also use type annotations
    - ``typing.Dict`` or ``dict`` gets converted into a dictionary object using json.loads 
    - ``int``, ``bool``, and ``float`` type annotations just get straight converted.
    - any type annotation with the staticmethod ``_coerce`` is used to convert the
      object using that method
    
.. code-block:: python

    import typing

    import figenv

    
    class csv:
        @staticmethod
        def _coerce(value):
            return value.split(',')

    class Config(metaclass=figenv.MetaConfig)
        DEBUG = 'false'
        VERSION = '1.2.3'
        FEATURE_FLAG_PERCENT = '0.24'
        ALLOWLIST_USERID: csv = '123abc,456efg'
        DATA: typing.Dict = '{"name":"george"}'

    assert Config.DEBUG == False
    assert Config.VERSION == '1.2.3'
    assert Config.FEATURE_FLAG_PERCENT == 0.24
    assert Config.ALLOWLIST_USERID == ['123abc', '456efg']
    assert Config.DATA == {'name': 'george'}

Data Access
-----------

The main intended way to access environment variables from figenv is to access
the config objects attributes.

Example:

.. code-block:: python

    import figenv

    class Config(metaclass=figenv.MetaConfig):
         TIMEOUT = 5


    assert Config.TIMEOUT == 5
    assert Config['TIMEOUT'] == 5
    for key, value in Config:
        if key == 'TIMEOUT':
            assert value == 5
    assert dict(Config) == {'TIMEOUT': 5}

But it can also see, you can use it by using the getitem method as if it was a
dictionary as well. You can also access the config key values in a for loop and
also convert the whole object to a dictionary if you want.

Load all environment variables
------------------------------

If for some reason you do not want to put all your configuration variables into
the config object, but still want to access other environment variables, set the
ENV_LOAD_ALL attribute on the config class, and it will pull values from the
environment even if they do not have a default set on the class.

.. code-block:: python

    >>> import figenv
    >>> class Config(metaclass=figenv.MetaConfig):
    ...   ENV_LOAD_ALL = True
    ...
    >>> Config.USER
    'wallacda'

Prefixes
--------

If you have want to add prefixes to all of the environment variables in your
config object, you can specify the ENV_PREFIX attribute.

.. code-block:: python

    >>> import figenv, os
    >>> class Config(metaclass=figenv.MetaConfig):
    ...   ENV_PREFIX = 'FIGENV_'
    ...   USER = 'daniel'
    ...
    >>> os.getenv('USER')
    'wallacda'
    >>> Config.USER
    'daniel'
    >>> os.environ['FIGENV_USER'] = 'newuser'
    >>> Config.USER
    'newuser'
