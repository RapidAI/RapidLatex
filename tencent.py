from tencentcloud.common import credential, exception
from tencentcloud.tmt.v20180321 import tmt_client
from config import config


class Translator:
    def __init__(self, secret_id=None, secret_key=None, region='ap-shanghai'):
        # Use provided credentials or fall back to config
        self.secret_id = secret_id or config.tencent_secret_id
        self.secret_key = secret_key or config.tencent_secret_key
        self.region = region or getattr(config, 'tencent_region', 'ap-shanghai')

        self.cred = credential.Credential(self.secret_id, self.secret_key)
        self.client = tmt_client.TmtClient(self.cred, self.region)

    def is_error_request_frequency(self, e: exception.TencentCloudSDKException):
        code = e.get_code()
        if code == 'RequestLimitExceeded':
            return True
        else:
            return False

    def normalize_language_code(self, lang_code):
        """Normalize language codes for Tencent Cloud"""
        # Map common language codes to Tencent Cloud supported codes
        language_mapping = {
            'zh-CN': 'zh',
            'zh-TW': 'zh-TW',
            'zh-Hans': 'zh',
            'zh-Hant': 'zh-TW',
            'en-US': 'en',
            'en-GB': 'en',
        }
        return language_mapping.get(lang_code, lang_code)

    def translate(self, text, language_to, language_from):
        # Normalize language codes for Tencent Cloud
        normalized_source = self.normalize_language_code(language_from)
        normalized_target = self.normalize_language_code(language_to)

        request = tmt_client.models.TextTranslateRequest()
        request.Source = normalized_source
        request.Target = normalized_target
        request.SourceText = text
        request.ProjectId = 0
        request.UntranslatedText = config.math_code
        result = self.client.TextTranslate(request)
        return result.TargetText
