import contextlib
import os
import typing
import unittest

import xmlrunner

from figenv import MetaConfig, strict, MissingConfigurationException, _MISSING


class TestEnv(unittest.TestCase):
    @contextlib.contextmanager
    def with_env(self, **kwargs):
        """Context manager to set temporary environment variables and then remove when done"""
        # Set environment variables
        os.environ.update(kwargs)

        # Yield to caller
        yield

        # Delete set variables
        for key in kwargs.keys():
            if key in os.environ:
                del os.environ[key]
        for key in ('ENV_LOAD_ALL', 'ENV_PREFIX'):
            if key in os.environ:
                del os.environ[key]

    def _get_test_configuration(self, env_prefix='', env_load_all=False, bases=None, **kwargs):
        """Helper to define a new configuration class using our MetaConfig"""
        if bases is None:
            bases = (object,)
        return MetaConfig('TestConfiguration', bases, dict(ENV_PREFIX=env_prefix, ENV_LOAD_ALL=env_load_all, **kwargs))

    def test_default_env_load_all(self):
        """A test to ensure that we load all environment variables by default"""
        # Configure an environment variable not defined on the configuration class
        with self.with_env(TEST_SETTING='true', DEFAULT_SETTING='set_by_env'):
            # Create our configuration object
            TestConfiguration = self._get_test_configuration(
                env_load_all=True,
                DEFAULT_SETTING='set_in_class',
            )

            self.assertEqual(TestConfiguration.DEFAULT_SETTING, 'set_by_env')

            # Assert that we only loaded defined settings from environment
            self.assertTrue(hasattr(TestConfiguration, 'TEST_SETTING'))

            with self.assertRaises(AttributeError):
                TestConfiguration.WHAT

        self.assertEqual(TestConfiguration.DEFAULT_SETTING, 'set_in_class')

    def test_default_settings(self):
        """A test to ensure that if no environment variable is set, we get the default value that is set"""
        TestConfiguration = self._get_test_configuration(
            DEFAULT_SETTING='default_value',
            BOOL_SETTING=True,
            __annotations__={"DEFAULT_SETTING": str, "NO_DEFAULT_SETTING": str, "BOOL_SETTING": bool},
        )
        self.assertEqual(TestConfiguration.DEFAULT_SETTING, 'default_value')
        self.assertIs(TestConfiguration.BOOL_SETTING, True)
        with self.assertRaises(RuntimeError):
            TestConfiguration.NO_DEFAULT_SETTING
        with self.assertRaises(RuntimeError):
            TestConfiguration["NO_DEFAULT_SETTING"]

    def test_invalid_setter(self):
        """users should not be able to set variables using attributes"""
        TestConfiguration = self._get_test_configuration(DEFAULT_SETTING='default_value', BOOL_SETTING=True)
        with self.assertRaises(NotImplementedError):
            TestConfiguration.DEFAULT_SETTING = 'hi'

    def test_coerce_settings(self):
        """A test to ensure that annotations are used to coerce variables"""

        class csv:
            @classmethod
            def _coerce(self, value):
                return value.split(',')

        class TestConfiguration(metaclass=MetaConfig):
            DEFAULT_SETTING: csv = 'default,value'
            BOOL_SETTING: bool = '1'
            FALSE_SETTING: bool = '0'
            INT_SETTING: int = '1093'
            FLOAT_SETTING: float = '1.938'
            DICT_SETTING: typing.Dict = '{"hello":"world"}'
            NO_DEFAULT_SETTING: int

        self.assertEqual(TestConfiguration.DEFAULT_SETTING, ['default', 'value'])
        self.assertIs(TestConfiguration.BOOL_SETTING, True)
        self.assertIs(TestConfiguration.FALSE_SETTING, False)
        self.assertEqual(TestConfiguration.INT_SETTING, 1093)
        self.assertEqual(TestConfiguration.FLOAT_SETTING, 1.938)
        self.assertEqual(TestConfiguration.DICT_SETTING, {'hello': 'world'})
        with self.with_env(NO_DEFAULT_SETTING="200"):
            self.assertEqual(TestConfiguration.NO_DEFAULT_SETTING, 200)

    def test_inherit_settings(self):
        """A test inheriting settings"""
        Parent = self._get_test_configuration(CLASS='parent', SECONDARY='second')
        Child = self._get_test_configuration(bases=(Parent,), CLASS='child')
        assert Child.CLASS == 'child'
        assert Parent.CLASS == 'parent'
        assert Child.SECONDARY == 'second'
        assert Parent.SECONDARY == 'second'

    def test_dict_update_settings(self):
        """A configuration class can be updated in a dict"""

        def func(cls):
            return 'hi'

        test = dict()
        settings = self._get_test_configuration(
            NAME='test', HELLO=func, __annotations__={'NAME': str, 'NO_DEFAULT': str}
        )
        with self.with_env(NO_DEFAULT='hello'):
            test.update(settings)
        assert test['HELLO'] == 'hi'
        assert test['NAME'] == 'test'
        assert test['NO_DEFAULT'] == 'hello'
        with self.assertRaises(KeyError):
            settings['UNSET']

    def test_iterate_settings(self):
        """A configuration class can be iterable"""

        def func(cls):
            return 'hi'

        settings = self._get_test_configuration(NAME='test', HELLO=func)
        test = {key: value for key, value in settings}
        assert test['HELLO'] == 'hi'
        assert test['NAME'] == 'test'

        with self.assertRaises(KeyError):
            settings['UNSET']

    def test_override_from_env(self):
        """A test to ensure that an environment variable will override the default setting"""
        with self.with_env(DEFAULT_SETTING='set_by_env'):
            TestConfiguration = self._get_test_configuration(DEFAULT_SETTING='default_value')
            self.assertEqual(TestConfiguration.DEFAULT_SETTING, 'set_by_env')

    def test_only_set_on_env(self):
        """A test to ensure that a setting only defined by an environment variable is still available"""
        with self.with_env(NEW_SETTING='set_by_env'):
            # When configured to load all environment variables
            TestConfiguration = self._get_test_configuration(env_load_all=True)
            self.assertEqual(TestConfiguration.NEW_SETTING, 'set_by_env')

            # When configured to not load all environment variables
            TestConfiguration = self._get_test_configuration(env_load_all=False)
            self.assertFalse(hasattr(TestConfiguration, 'NEW_SETTING'))

    def test_env_prefix(self):
        """A test to ensure that the ENV_PREFIX setting functions as needed"""
        with self.with_env(TEST_DEFAULT_SETTING='set_by_env'):
            TestConfiguration = self._get_test_configuration(env_prefix='TEST_', DEFAULT_SETTING='default_value')
            self.assertEqual(TestConfiguration.DEFAULT_SETTING, 'set_by_env')

    def test_env_prefix_non_matching(self):
        """A test to ensure that the ENV_PREFIX setting does not allow non-matching settings in"""
        with self.with_env(DEFAULT_SETTING='set_by_env'):
            TestConfiguration = self._get_test_configuration(env_prefix='MYAPP_', DEFAULT_SETTING='default_value')
            self.assertEqual(TestConfiguration.DEFAULT_SETTING, 'default_value')

    def test_parsing_boolean(self):
        """A test to ensure that we properly parse booleans"""

        class TestConfiguration(metaclass=MetaConfig):
            # DEV: Set `env_load_all=True` to keep from having to make default values for each variable
            ENV_LOAD_ALL = True
            # Annotation should force type coercion to bool
            DEFINED_ANNOTATED_BOOL_BOOL_STRING: bool = False
            DEFINED_ANNOTATED_BOOL_INT_STRING: bool = False
            # Annotation should force type coercion to str
            DEFINED_ANNOTATED_STRING_BOOL_STRING: str = "False"
            # Type coercion should default based on value (Same behaviour as undefined values loaded from env)
            DEFINED_UNANNOTATED = None

        truth_env = dict(
            ENV_BOOL_LOWER='true',
            ENV_BOOL_UPPER='TRUE',
            ENV_BOOL_CAP='True',
            ENV_BOOL_WACKY='TrUe',
            ENV_NOT_BOOL="true-ish",
            DEFINED_ANNOTATED_BOOL_BOOL_STRING="true",
            DEFINED_ANNOTATED_BOOL_INT_STRING="1",
            DEFINED_ANNOTATED_STRING_BOOL_STRING="true",
            DEFINED_UNANNOTATED="True",
        )
        with self.with_env(**truth_env):
            self.assertEqual(TestConfiguration.ENV_BOOL_LOWER, True)
            self.assertEqual(TestConfiguration.ENV_BOOL_UPPER, True)
            self.assertEqual(TestConfiguration.ENV_BOOL_CAP, True)
            self.assertEqual(TestConfiguration.ENV_BOOL_WACKY, True)
            self.assertEqual(TestConfiguration.ENV_NOT_BOOL, 'true-ish')
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_BOOL_BOOL_STRING, True)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_BOOL_INT_STRING, True)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_STRING_BOOL_STRING, "true")
            self.assertEqual(TestConfiguration.DEFINED_UNANNOTATED, True)

        false_env = dict(
            ENV_BOOL_LOWER='false',
            ENV_BOOL_UPPER='FALSE',
            ENV_BOOL_CAP='False',
            ENV_BOOL_WACKY='FaLSe',
            ENV_NOT_BOOL="falsish",
            DEFINED_ANNOTATED_BOOL_BOOL_STRING="false",
            DEFINED_ANNOTATED_BOOL_INT_STRING="0",
            DEFINED_ANNOTATED_STRING_BOOL_STRING="False",
            DEFINED_UNANNOTATED="False",
        )

        with self.with_env(**false_env):
            self.assertEqual(TestConfiguration.ENV_BOOL_LOWER, False)
            self.assertEqual(TestConfiguration.ENV_BOOL_UPPER, False)
            self.assertEqual(TestConfiguration.ENV_BOOL_CAP, False)
            self.assertEqual(TestConfiguration.ENV_BOOL_WACKY, False)
            self.assertEqual(TestConfiguration.ENV_NOT_BOOL, 'falsish')
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_BOOL_BOOL_STRING, False)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_BOOL_INT_STRING, False)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_STRING_BOOL_STRING, "False")
            self.assertEqual(TestConfiguration.DEFINED_UNANNOTATED, False)

    def test_parsing_float(self):
        """A test to ensure that we properly parse floats"""

        class TestConfiguration(metaclass=MetaConfig):
            # DEV: Set `env_load_all=True` to keep from having to make default values for each variable
            ENV_LOAD_ALL = True
            # Annotation should force type coercion to float
            DEFINED_ANNOTATED_FLOAT_FLOAT_STRING: float = 0.0
            DEFINED_ANNOTATED_FLOAT_INT_STRING: float = 0.0
            # Annotation should force type coercion to str
            DEFINED_ANNOTATED_STRING_FLOAT_STRING: str = "0.0"
            # Type coercion should default based on value (Same behaviour as undefined values loaded from env)
            DEFINED_UNANNOTATED = None

        env = dict(
            ENV_FLOAT='12.5',
            ENV_ZERO_FLOAT='0.0',
            ENV_NEGATIVE_FLOAT='-13.4',
            ENV_TRAILING_DOT_FLOAT='12.',
            ENV_LEADING_DOT_FLOAT='.12',
            ENV_NOT_FLOAT='This is 6.5',
            DEFINED_ANNOTATED_FLOAT_FLOAT_STRING="67.54",
            DEFINED_ANNOTATED_FLOAT_INT_STRING="32",
            DEFINED_ANNOTATED_STRING_FLOAT_STRING="107.3",
            DEFINED_UNANNOTATED="6.75",
        )
        with self.with_env(**env):
            self.assertEqual(TestConfiguration.ENV_FLOAT, 12.5)
            self.assertEqual(TestConfiguration.ENV_ZERO_FLOAT, 0.0)
            self.assertEqual(TestConfiguration.ENV_NEGATIVE_FLOAT, -13.4)
            self.assertEqual(TestConfiguration.ENV_TRAILING_DOT_FLOAT, 12.0)
            self.assertEqual(TestConfiguration.ENV_LEADING_DOT_FLOAT, 0.12)
            self.assertEqual(TestConfiguration.ENV_NOT_FLOAT, 'This is 6.5')
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_FLOAT_FLOAT_STRING, 67.54)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_FLOAT_INT_STRING, 32.0)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_STRING_FLOAT_STRING, "107.3")
            self.assertEqual(TestConfiguration.DEFINED_UNANNOTATED, 6.75)

    def test_parsing_int(self):
        """A test to ensure that we properly parse integers"""

        class TestConfiguration(metaclass=MetaConfig):
            # DEV: Set `env_load_all=True` to keep from having to make default values for each variable
            ENV_LOAD_ALL = True
            # Annotation should force type coercion to float
            DEFINED_ANNOTATED_INT_INT_STRING: int = 0
            # Annotation should force type coercion to str
            DEFINED_ANNOTATED_STRING_INT_STRING: str = "0"
            # Type coercion should default based on value (Same behaviour as undefined values loaded from env)
            DEFINED_UNANNOTATED = None

        env = dict(
            ENV_INT='12',
            ENV_ZERO_INT='0',
            ENV_NEGATIVE_INT="-12",
            ENV_NOT_INT='12fa',
            DEFINED_ANNOTATED_INT_INT_STRING="42",
            DEFINED_ANNOTATED_STRING_INT_STRING="69",
            DEFINED_UNANNOTATED="420",
        )
        with self.with_env(**env):
            self.assertEqual(TestConfiguration.ENV_INT, 12)
            self.assertEqual(TestConfiguration.ENV_ZERO_INT, 0)
            self.assertEqual(TestConfiguration.ENV_NEGATIVE_INT, -12)
            self.assertEqual(TestConfiguration.ENV_NOT_INT, '12fa')
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_INT_INT_STRING, 42)
            self.assertEqual(TestConfiguration.DEFINED_ANNOTATED_STRING_INT_STRING, "69")
            self.assertEqual(TestConfiguration.DEFINED_UNANNOTATED, 420)

    def test_parsing_dict(self):
        """A test to ensure we properly parse dictionaries"""

        class TestingConfig(metaclass=MetaConfig):
            MY_MAPPING: dict = None

        with self.with_env(MY_MAPPING='{"int": 1, "bool": true, "float": 7.4, "string": "hello"}'):
            self.assertDictEqual(TestingConfig.MY_MAPPING, {"int": 1, "bool": True, "float": 7.4, "string": "hello"})

    def test_parsing_list(self):
        """A test to ensure we properly parse lists"""

        class TestingConfig(metaclass=MetaConfig):
            MY_LIST: list = None

        with self.with_env(MY_LIST='[true, 1, 7.4, "hello", "\\"Never Give Up, Never Surrender\\""]'):
            self.assertListEqual(TestingConfig.MY_LIST, [True, 1, 7.4, "hello", "\"Never Give Up, Never Surrender\""])

    def test_parsing_version_string(self):
        """A test to ensure that we properly parse version strings as strings"""
        env = dict(VERSION_STRING='1.0.2')
        with self.with_env(**env):
            # DEV: Set `env_load_all=True` to keep from having to make default values for each variable
            TestConfiguration = self._get_test_configuration(env_load_all=True)
            self.assertEqual(TestConfiguration.VERSION_STRING, '1.0.2')

    def test_parsing_custom_type_via_coerce(self):
        class CSV:
            @classmethod
            def _coerce(cls, value: str):
                if not value.startswith("[") and value.endswith("]"):
                    raise ValueError(f"Invalid literal for csv: '{value}")
                return value.strip("[]").split(",")

        class TestingConfig(metaclass=MetaConfig):
            MY_CSV_LIST: CSV = None

        with self.with_env(MY_CSV_LIST="[A,B,C]"):
            self.assertEqual(TestingConfig.MY_CSV_LIST, ["A", "B", "C"])

    def test_parsing_custom_type_via_to_x(self):
        class Role:
            ADMIN = object()
            USER = object()

        class TestingConfig(metaclass=MetaConfig):
            MY_ROLE: Role = Role.USER

            @staticmethod
            def _to_role(value: str):
                if value == "ADMIN":
                    return Role.ADMIN
                else:
                    return Role.USER

        with self.with_env(MY_ROLE="ADMIN"):
            self.assertEqual(TestingConfig.MY_ROLE, Role.ADMIN)

    def test_classmethod_functions(self):
        """A test to ensure that we properly parse integers"""

        def func(cls):
            return cls.DATA + '123'

        TestConfiguration = self._get_test_configuration(DATA='blah', FUNC=func)
        self.assertEqual(TestConfiguration.FUNC, 'blah123')
        assert 'FUNC' in dir(TestConfiguration)

    def test_override_from_env_functions(self):
        """A test to ensure that functions are overridden with environment values"""

        def func(cls):
            return cls.DATA + ' world'

        def func_num(cls) -> str:
            return '123456'

        with self.with_env(GREETING='hola mundo'):
            TestConfiguration = self._get_test_configuration(DATA='hello', GREETING=func, ACCOUNT_ID=func_num)
            assert 'GREETING' in dir(TestConfiguration)
            self.assertEqual(TestConfiguration.GREETING, 'hola mundo')
            self.assertEqual(TestConfiguration.ACCOUNT_ID, '123456')

    def test_strict_functions(self):
        """A test to ensure that strict functions are NOT overridden with environment values"""

        @strict
        def func(cls):
            return cls.DATA + ' world'

        with self.with_env(GREETING='hola mundo'):
            TestConfiguration = self._get_test_configuration(DATA='hello', GREETING=func)
            assert 'GREETING' in dir(TestConfiguration)
            self.assertEqual(TestConfiguration.GREETING, 'hello world')


class TestMissing(unittest.TestCase):
    """Pointless tests for code coverage"""

    def test_representation(self):
        value = _MISSING
        self.assertEqual(str(value), "<MISSING CONFIGURATION>")

    def test_exception_default(self):
        exception = MissingConfigurationException("MY_VALUE")
        self.assertEqual(exception.name, "MY_VALUE")
        self.assertEqual(str(exception), "Configuration 'MY_VALUE' is not present in environment")

    def test_exception_custom_message(self):
        exception = MissingConfigurationException("MY_VALUE", "Invalid Configuration! Please provide MY_VALUE.")
        self.assertEqual(exception.name, "MY_VALUE")
        self.assertEqual(str(exception), "Invalid Configuration! Please provide MY_VALUE.")


if __name__ == '__main__':
    with open('xunit.xml', 'wb') as fh_:
        unittest.main(testRunner=xmlrunner.XMLTestRunner(output=fh_))
