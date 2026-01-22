import os
import md_parser
import config

class ConfigManager:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(root_dir, "CONFIG.md")

        if os.path.exists(config_path):
            self._config = md_parser.parse_config_md(config_path)
        else:
            self._config = {}

    def get(self, key, default=None):
        return self._config.get(key, default)

    def get_prompt(self, agent_name, default_template):
        prompts = self._config.get("prompts", {})
        return prompts.get(agent_name, default_template)

    @property
    def openai_api_key(self):
        return self.get("OPENAI_API_KEY") or config.OPENAI_API_KEY

    @property
    def openai_base_url(self):
        return self.get("OPENAI_BASE_URL") or config.OPENAI_BASE_URL

# Global instance
config_manager = ConfigManager()
