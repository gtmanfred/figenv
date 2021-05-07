import json
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
        if name in ('__annotations__', 'name', '_dict', '_to_int', '_to_bool', '_to_float', '_to_dict'):
            return super().__getattribute__(name)
        raise AttributeError('Fallback to environment')

    def __dir__(cls):
        return list(cls._dict)

    def _to_bool(cls, value):
        if value.lower() in ('yes', 'true', '1'):
            return True
        return False

    def _to_int(cls, value):
        return int(value)

    def _to_float(cls, value):
        return float(value)

    def _to_dict(cls, value):
        return json.loads(value)

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

        if callable(value):
            value = value(cls)

        annotation = getattr(cls, '__annotations__', {}).get(name, None)
        if annotation is not None:
            annoname = getattr(annotation, '_name', getattr(annotation, '__name__', None))
            coerce_func = getattr(annotation, '_coerce', getattr(cls, f'_to_{annoname.lower()}', None))

        if not isinstance(value, str):
            return value
        elif annotation is not None and coerce_func is not None:
            value = coerce_func(value)
        elif value.lower() in ('true', 'false'):
            value = True if value.lower() == 'true' else False
        elif value.count('.') == 1 and ''.join(filter(lambda x: x != '.', value)).isdigit():
            value = float(value)
        elif value.isdigit():
            value = int(value)

        return value
