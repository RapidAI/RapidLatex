import os
import json
import appdata
app_paths = appdata.AppDataPaths('mathtranslate')
app_dir = app_paths.app_data_path
default_dir = os.path.join(app_dir, 'default')
os.makedirs(default_dir, exist_ok=True)

# JSON config file path
config_json_path = os.path.join(app_dir, 'config.json')


class Config:
    default_engine_path = 'DEFAULT_ENGINE'
    default_language_from_path = 'DEFAULT_LANGUAGE_FROM'
    default_language_to_path = 'DEFAULT_LANGUAGE_TO'
    default_loading_dir_path = 'DEFAULT_LOADING_DIR'
    default_saving_dir_path = 'DEFAULT_SAVING_DIR'
    default_threads_path = 'DEFAULT_THREADS'
    tencent_secret_id_path = 'TENCENT_ID'
    tencent_secret_key_path = 'TENCENT_KEY'
    openai_api_key_path = 'OPENAI_API_KEY'
    openai_base_url_path = 'OPENAI_BASE_URL'
    openai_model_path = 'OPENAI_MODEL'
    openai_max_tokens_path = 'OPENAI_MAX_TOKENS'
    openai_temperature_path = 'OPENAI_TEMPERATURE'
    openai_chunk_size_path = 'OPENAI_CHUNK_SIZE'
    tencent_secret_id_path = 'TENCENT_SECRET_ID'
    tencent_secret_key_path = 'TENCENT_SECRET_KEY'
    tencent_region_path = 'TENCENT_REGION'

    default_engine_default = 'google'
    default_language_from_default = 'en'
    default_language_to_default = 'zh-CN'
    default_loading_dir_default = os.path.expanduser("~")
    default_saving_dir_default = os.path.expanduser("~")
    default_threads_default = 0
    tencent_secret_id_default = None
    tencent_secret_key_default = None
    openai_api_key_default = None
    openai_base_url_default = "https://api.openai.com/v1"
    openai_model_default = "gpt-3.5-turbo"
    openai_max_tokens_default = 2000
    openai_temperature_default = 0.3
    openai_chunk_size_default = 3000
    tencent_secret_id_default = None
    tencent_secret_key_default = None
    tencent_region_default = 'ap-shanghai'

    math_code = 'XMATHX'
    log_file = f'{app_dir}/translate_log'
    raw_mularg_command_list = [('textcolor', 2, (1, 2))]
    mularg_command_list = [('textcolor', 2, (1, 2))]

    # Custom environment and command settings
    custom_environments = []
    custom_commands = []
    skip_environments = ['equation', 'align', 'gather', 'displaymath', 'eqnarray']  # These should not be translated
    skip_commands = ['ref', 'label', 'cite', 'citep', 'citet', 'bibitem', 'bibliographystyle', 'bibliography', 'XMATHX', 'XMATHXBS']  # These should not be translated

    def __init__(self):
        self.load()
        if os.path.exists(f'{app_dir}/TEST'):
            self.test_environment = True
            print('This is a test environment!')
        else:
            self.test_environment = False

    @staticmethod
    def read_variable(path, default):
        if os.path.exists(f'{default_dir}/{path}'):
            return open(f'{default_dir}/{path}').read().replace(' ', '').replace('\n', '')
        else:
            return default

    @staticmethod
    def set_variable(path, default):
        var = input().replace(' ', '').replace('\n', '')
        if var != '':
            print(var, file=open(f'{default_dir}/{path}', 'w'))

    @staticmethod
    def set_variable_4ui(path, var):
        print(var, file=open(f'{default_dir}/{path}', 'w'))

    def load_json_config(self):
        """Load configuration from JSON file"""
        # First try to load from local directory, then from appdata directory
        local_config_path = 'config.json'

        for path in [local_config_path, config_json_path]:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        json_config = json.load(f)
                        if path == local_config_path:
                            print(f"Loaded config from local directory: {path}")
                        else:
                            print(f"Loaded config from appdata directory: {path}")
                        return json_config
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load {path}: {e}")
                    continue
        return {}

    def save_json_config(self, config_data):
        """Save configuration to JSON file"""
        try:
            with open(config_json_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, TypeError) as e:
            print(f"Error: Failed to save config.json: {e}")
            return False

    def read_json_value(self, key, default):
        """Read value from JSON config, fallback to default"""
        json_config = self.load_json_config()
        return json_config.get(key, default)

    def set_json_value(self, key, value):
        """Set value in JSON config"""
        json_config = self.load_json_config()
        json_config[key] = value
        return self.save_json_config(json_config)

    def load(self):
        self.default_engine = self.read_variable(self.default_engine_path, self.default_engine_default)
        self.default_language_from = self.read_variable(self.default_language_from_path, self.default_language_from_default)
        self.default_language_to = self.read_variable(self.default_language_to_path, self.default_language_to_default)
        # Read OpenAI and Tencent configuration from JSON file
        json_config = self.load_json_config()

        # Support both flat and nested structure for OpenAI
        if 'openai' in json_config and isinstance(json_config['openai'], dict):
            # Nested structure: {"openai": {"api_key": "..."}}
            openai_config = json_config['openai']
            self.openai_api_key = openai_config.get('api_key', self.openai_api_key_default)
            self.openai_base_url = openai_config.get('base_url', self.openai_base_url_default)
            self.openai_model = openai_config.get('model', self.openai_model_default)
            self.openai_max_tokens = openai_config.get('max_tokens', self.openai_max_tokens_default)
            self.openai_temperature = openai_config.get('temperature', self.openai_temperature_default)
            self.openai_chunk_size = openai_config.get('chunk_size', self.openai_chunk_size_default)
        else:
            # Flat structure: {"openai_api_key": "..."}
            self.openai_api_key = json_config.get('openai_api_key', self.openai_api_key_default)
            self.openai_base_url = json_config.get('openai_base_url', self.openai_base_url_default)
            self.openai_model = json_config.get('openai_model', self.openai_model_default)
            self.openai_max_tokens = json_config.get('openai_max_tokens', self.openai_max_tokens_default)
            self.openai_temperature = json_config.get('openai_temperature', self.openai_temperature_default)
            self.openai_chunk_size = json_config.get('openai_chunk_size', self.openai_chunk_size_default)

        # Support both flat and nested structure for Tencent
        if 'tencent' in json_config and isinstance(json_config['tencent'], dict):
            # Nested structure: {"tencent": {"secret_id": "..."}}
            tencent_config = json_config['tencent']
            self.tencent_secret_id = tencent_config.get('secret_id', self.tencent_secret_id_default)
            self.tencent_secret_key = tencent_config.get('secret_key', self.tencent_secret_key_default)
            self.tencent_region = tencent_config.get('region', self.tencent_region_default)
        else:
            # Flat structure: {"tencent_secret_id": "..."}
            self.tencent_secret_id = json_config.get('tencent_secret_id', self.tencent_secret_id_default)
            self.tencent_secret_key = json_config.get('tencent_secret_key', self.tencent_secret_key_default)
            self.tencent_region = json_config.get('tencent_region', self.tencent_region_default)

        # Fallback to file-based config if JSON doesn't have the values
        if not self.tencent_secret_id:
            self.tencent_secret_id = self.read_variable(self.tencent_secret_id_path, self.tencent_secret_id_default)
        if not self.tencent_secret_key:
            self.tencent_secret_key = self.read_variable(self.tencent_secret_key_path, self.tencent_secret_key_default)
        self.default_loading_dir = self.read_variable(self.default_loading_dir_path, self.default_loading_dir_default)
        self.default_saving_dir = self.read_variable(self.default_saving_dir_path, self.default_saving_dir_default)
        self.default_threads = int(self.read_variable(self.default_threads_path, self.default_threads_default))
        if not os.path.exists(self.default_loading_dir):
            self.default_loading_dir = self.default_loading_dir_default
        if not os.path.exists(self.default_saving_dir):
            self.default_saving_dir = self.default_saving_dir_default

        # Load custom environment and command settings
        self.custom_environments = json_config.get('custom_environments', self.custom_environments)
        self.custom_commands = json_config.get('custom_commands', self.custom_commands)
        self.skip_environments = json_config.get('skip_environments', self.skip_environments)
        self.skip_commands = json_config.get('skip_commands', self.skip_commands)


config = Config()
