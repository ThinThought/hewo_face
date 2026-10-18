import importlib
import pathlib
import yaml
import logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] - %(name)s - %(message)s')

DEBUG = False


def create_logger(name):
    msg = "LOGGER INIT FOR OBJECT - " + name
    logger = logging.getLogger(name)
    if DEBUG:
        logger.setLevel(logging.DEBUG)
        msg += " - in DEBUG mode"
    else:
        logger.setLevel(logging.INFO)
        msg += " - in INFO mode"

    logger.info(msg)
    return logger

class SettingsLoader:
    def __init__(self, module_name=None):
        self.settings_path = None
        self.settings = {}
        if module_name is not None:
            self.load_settings(module_name)

    def load_settings(self, module_name):
        module = importlib.import_module(module_name)
        settings_path = pathlib.Path(module.__file__).parent

        if not settings_path.exists() or not settings_path.is_dir():
            raise FileNotFoundError(f"No se encontró el directorio de settings en: {settings_path}")

        setting_files = sorted(settings_path.glob('*.yaml'))
        if not setting_files:
            raise FileNotFoundError(f"No YAML settings found in: {settings_path}")

        loaded = {}
        for setting_file in setting_files:
            with setting_file.open('r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or {}
            if not isinstance(data, dict):
                raise ValueError(f"Settings file must contain a mapping: {setting_file}")
            loaded.update(data)

        self.settings = loaded
        self.settings_files = tuple(setting_files)
        self.settings_path = setting_files[0] if len(setting_files) == 1 else None
        return dict(self.settings)

    def pretty_print(self):
        print(yaml.dump(self.settings, default_flow_style=False, sort_keys=False, allow_unicode=True))

    def save_settings(self, settings):
        if self.settings_path is None:
            raise ValueError("Cannot save merged settings; load a directory with exactly one YAML file")
        with self.settings_path.open('w', encoding='utf-8') as file:
            yaml.safe_dump(settings, file, default_flow_style=False, sort_keys=False, allow_unicode=True)
