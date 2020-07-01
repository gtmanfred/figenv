import os


class MetaConfig(type):
    def __init__(cls, name, bases, dict):
        super().__init__(name, bases, dict)
        cls.name = name
        cls._dict = dict

    def __getattribute__(cls, name):
        '''
        Return value of ``name`` and ``_dict``

        Fall back to getattr for everything else
        '''
        if name in ('name', '_dict'):
            return super().__getattribute__(name)
        raise AttributeError('Fallback to environment')

    def __getattr__(cls, name):
        '''
        Check if attribute is available on the class. If it is, then check
        the environment variables for that. If it is not in the environment
        variables, then return the default set on the class. Otherwise raise
        an AttributeError.
        '''
        prefix = cls._dict.get('ENV_PREFIX', '')
        load_all = cls._dict.get('ENV_LOAD_ALL', False)

        if (not load_all and name not in cls._dict) or (name not in cls._dict and prefix + name not in os.environ):
            raise AttributeError(f"type object {cls.name} has no attribute '{name}'")

        if prefix + name in os.environ:
            value = os.environ[prefix + name]
        else:
            value = cls._dict[name]

        if not isinstance(value, str):
            return value
        elif value.lower() in ('true', 'false'):
            value = True if value.lower() == 'true' else False
        elif '.' in value and ''.join(filter(lambda x: x != '.', value)).isdigit():
            value = float(value)
        elif value.isdigit():
            value = int(value)

        return value
