import os
__version__ = open(os.path.join(os.path.dirname(__file__), 'version.txt'), encoding='utf-8').read().strip()
from config import config, config_json_path
from update import get_latest_version
import sys
import re
language_list = '''
Afrikaans            af
Irish                ga
Albanian             sq
Italian              it
Arabic               ar
Japanese             ja
Azerbaijani          az
Kannada              kn
Basque               eu
Korean               ko
Bengali              bn
Latin                la
Belarusian           be
Latvian              lv
Bulgarian            bg
Lithuanian           lt
Catalan              ca
Macedonian           mk
Chinese_Simplified   zh-CN
Malay                ms
Chinese_Traditional  zh-TW
Maltese              mt
Croatian             hr
Norwegian            no
Czech                cs
Persian              fa
Danish               da
Polish               pl
Dutch                nl
Portuguese           pt
English              en
Romanian             ro
Esperanto            eo
Russian              ru
Estonian             et
Serbian              sr
Filipino             tl
Slovak               sk
Finnish              fi
Slovenian            sl
French               fr
Spanish              es
Galician             gl
Swahili              sw
Georgian             ka
Swedish              sv
German               de
Tamil                ta
Greek                el
Telugu               te
Gujarati             gu
Thai                 th
Haitian_Creole       ht
Turkish              tr
Hebrew               iw
Ukrainian            uk
Hindi                hi
Urdu                 ur
Hungarian            hu
Vietnamese           vi
Icelandic            is
Welsh                cy
Indonesian           id
Yiddish              yi
'''

split = lambda s: re.split(r'\s+', s)


def check_update(require_updated=True):
    latest = get_latest_version()
    updated = __version__ == latest
    if updated:
        print("The current mathtranslate is latest")
    else:
        print("The current mathtranslate is not latest, please update by `pip install --upgrade mathtranslate`")
        if (not config.test_environment) and require_updated:
            sys.exit()


def add_arguments(parser):
    parser.add_argument("-engine", default=config.default_engine, help=f'translation engine, avaiable options include google, tencent, and openai. default is {config.default_engine}')
    parser.add_argument("-from", default=config.default_language_from, dest='l_from', help=f'language from, default is {config.default_language_from}')
    parser.add_argument("-to", default=config.default_language_to, dest='l_to', help=f'language to, default is {config.default_language_to}')
    parser.add_argument("-threads", default=config.default_threads, type=int, help='threads for tencent translation, default is auto')
    parser.add_argument("-commands", type=str, help='add commands for translation from a file')
    parser.add_argument("--force-utf8", action='store_true', help='force reading file by utf8')
    parser.add_argument("--list", action='store_true', help='list codes for languages')
    parser.add_argument("--setkey", action='store_true', help='set id and key of tencent translator')
    parser.add_argument("--setopenaikey", action='store_true', help='set api key and configuration of openai translator')
    parser.add_argument("--setdefault", action='store_true', help='set default translation engine and languages')
    parser.add_argument("--debug", action='store_true', help='Debug options for developers')
    parser.add_argument("--nocache", action='store_true', help='Debug options for developers')


def process_options(options):
    if options.setkey:
        print('Tencent secretID')
        config.set_variable(config.tencent_secret_id_path, config.tencent_secret_id_default)
        print('Tencent secretKey')
        config.set_variable(config.tencent_secret_key_path, config.tencent_secret_key_default)
        print('saved!')
        config.load()
        print('secretID:', config.tencent_secret_id)
        print('secretKey:', config.tencent_secret_key)
        sys.exit()

    if options.setdefault:
        print('Translation engine (google, tencent, or openai, default google)')
        config.set_variable(config.default_engine_path, config.default_engine_default)
        print('Translation language from (default en)')
        config.set_variable(config.default_language_from_path, config.default_language_from_default)
        print('Translation language to (default zh-CN)')
        config.set_variable(config.default_language_to_path, config.default_language_to_default)
        print('saved!')
        config.load()
        print('engine:', config.default_engine)
        print('language from:', config.default_language_from)
        print('language to:', config.default_language_to)
        sys.exit()

    if options.setopenaikey:
        print('Configuring OpenAI API settings (will be saved to config.json)')

        # Get OpenAI API key
        api_key = input('OpenAI API key: ').strip()
        if api_key:
            config.set_json_value('openai_api_key', api_key)

        # Get OpenAI Base URL
        base_url = input('OpenAI Base URL (default: https://api.openai.com/v1): ').strip()
        if not base_url:
            base_url = config.openai_base_url_default
        config.set_json_value('openai_base_url', base_url)

        # Get OpenAI Model
        model = input('OpenAI Model (default: gpt-3.5-turbo): ').strip()
        if not model:
            model = config.openai_model_default
        config.set_json_value('openai_model', model)

        # Get OpenAI Max Tokens
        max_tokens_str = input('OpenAI Max Tokens (default: 2000): ').strip()
        if not max_tokens_str:
            max_tokens = config.openai_max_tokens_default
        else:
            try:
                max_tokens = int(max_tokens_str)
            except ValueError:
                print(f'Invalid max_tokens value, using default: {config.openai_max_tokens_default}')
                max_tokens = config.openai_max_tokens_default
        config.set_json_value('openai_max_tokens', max_tokens)

        # Get OpenAI Temperature
        temperature_str = input('OpenAI Temperature (default: 0.3): ').strip()
        if not temperature_str:
            temperature = config.openai_temperature_default
        else:
            try:
                temperature = float(temperature_str)
            except ValueError:
                print(f'Invalid temperature value, using default: {config.openai_temperature_default}')
                temperature = config.openai_temperature_default
        config.set_json_value('openai_temperature', temperature)

        print('Configuration saved to config.json!')

        # Reload configuration and display
        config.load()
        print('API key:', config.openai_api_key[:10] + '...' if config.openai_api_key else 'None')
        print('Base URL:', config.openai_base_url)
        print('Model:', config.openai_model)
        print('Max tokens:', config.openai_max_tokens)
        print('Temperature:', config.openai_temperature)
        print('Config file location:', config_json_path)
        sys.exit()

    if options.list:
        print(language_list)
        print('tencent translator does not support some of them')
        sys.exit()

    if options.force_utf8:
        from . import encoding
        encoding.force_utf8 = True

    if options.engine == 'tencent':
        haskey = (config.tencent_secret_id is not None) and (config.tencent_secret_key is not None)
        if not haskey:
            print('Please save ID and key for tencent translation api first by')
            print('translate_tex --setkey')
            sys.exit()
        if options.l_from == 'zh-CN':
            options.l_from = 'zh'
        if options.l_to == 'zh-CN':
            options.l_to = 'zh'
        if options.threads == 0:
            options.threads = 1
        elif options.threads > 1:
            options.threads = 1
            print('tencent engine does not support multi-threading, set to 1')

    if options.engine == 'openai':
        haskey = config.openai_api_key is not None
        if not haskey:
            print('Please save OpenAI API key first by')
            print('translate_tex --setopenaikey')
            sys.exit()
        # OpenAI supports multi-threading, no need to modify threads setting

    if options.threads < 0:
        print('threads must be a non-zero integer number (>=0 where 0 means auto), set to auto')
        options.threads = 0

    additional_commands = []

    # Load default additional commands file if it exists
    project_root = os.path.dirname(os.path.abspath(__file__))
    default_commands_file = os.path.join(project_root, 'MT_additional_commands.txt')

    if os.path.exists(default_commands_file):
        try:
            content = open(default_commands_file, 'r', encoding='utf-8').read()
            var = {}
            exec(content, var)
            additional_commands.extend(var['additional_commands'])
            print(f'Loaded additional commands from: {default_commands_file}')
        except Exception as e:
            print(f'Warning: Failed to load {default_commands_file}: {e}')

    # Load user-specified commands file if provided
    if options.commands:
        try:
            content = open(options.commands, 'r', encoding='utf-8').read()
            var = {}
            exec(content, var)
            additional_commands.extend(var['additional_commands'])
            print(f'Loaded additional commands from: {options.commands}')
        except Exception as e:
            print(f'Error: Failed to load {options.commands}: {e}')
            sys.exit(1)

    config.mularg_command_list = config.raw_mularg_command_list + additional_commands

    print("Start")
    print('engine', options.engine)
    print('language from', options.l_from)
    print('language to', options.l_to)

    print('threads', options.threads if options.threads > 0 else 'auto')
    print()
