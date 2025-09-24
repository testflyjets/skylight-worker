import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import redis
from dotenv import load_dotenv

from selenium_worker.enums import BrowserDriverType, WorkerType

task_reject_on_worker_lost = True  # no ack if worker killed
broker_connection_retry_on_startup = True
health_check_interval = 0.25
worker_proc_alive_timeout = 240
worker_prefetch_multiplier = 1
worker_send_task_events = True
task_send_sent_event = True

# Time synchronization settings to prevent clock drift warnings
worker_disable_rate_limits = True
worker_enable_remote_control = True
worker_send_task_events = True
task_send_sent_event = True
task_track_started = True
task_time_limit = 30 * 60  # 30 minutes
task_soft_time_limit = 25 * 60  # 25 minutes
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 200000  # 200MB

# Redis broker transport options for better time handling
broker_transport_options = {
    'visibility_timeout': 3600,
    'fanout_prefix': True,
    'fanout_patterns': True,
    'socket_keepalive': True,
    'retry_on_timeout': True,
    'health_check_interval': 30,
}

# Result backend settings
result_backend_transport_options = {
    'retry_on_timeout': True,
    'socket_keepalive': True,
}

load_dotenv()

logger = logging.getLogger(__name__)

def get_config():
    return {
        'general': GeneralSettings.to_string(), 
        'api': APISettings.to_string(), 
        'redis': RedisSettings.to_string(),
        'proxy': ProxySettings.to_string(),
        'cache': CacheSettings.to_string(),
        'nopecha': NopeCHASettings.to_string(), 
        'browser': BrowserSettings.to_string(),
        'airnoise': AirnoiseSettings.to_string()
    }

class BaseConfig:
    def __init__(self):
        for attr, value in self.__class__.__dict__.items():
            if not attr.startswith('__') and value is None:
                logger.warning(f'{self.__class__.__name__}: attribute "{attr}" is not in .env')


class GeneralSettings(BaseConfig):
    ENVIRONMENT = 'dev' if not os.getenv('ENVIRONMENT') else os.getenv('ENVIRONMENT')
    WORKER_UID = uuid.uuid4().__str__() if not os.getenv("WORKER_UID") else os.getenv("WORKER_UID")
    BROWSER_DRIVER_TYPE = 'chrome' if not os.getenv('BROWSER_DRIVER_TYPE') else os.getenv('BROWSER_DRIVER_TYPE')
    WORKER_TYPE = 'KGAI' if not os.getenv('WORKER_TYPE') else os.getenv('WORKER_TYPE')

    @staticmethod
    def browser_driver_type() -> BrowserDriverType:
        browser_driver_value = GeneralSettings.BROWSER_DRIVER_TYPE
        if browser_driver_value == 'chrome':
            return BrowserDriverType.Chrome

        return BrowserDriverType.Unknown

    @staticmethod
    def worker_type() -> WorkerType:
        worker_value = GeneralSettings.WORKER_TYPE
        if worker_value == 'KGAI':
            return WorkerType.Montgomery
        elif worker_value == 'FAA':
            return WorkerType.FAA

        return WorkerType.Unknown

    @staticmethod
    def to_string():
        return "ENV={}, WORKER_UID={}, BROWSER_DRIVER_TYPE={}".format(
            GeneralSettings.ENVIRONMENT, GeneralSettings.WORKER_UID,
            GeneralSettings.BROWSER_DRIVER_TYPE)


class NopeCHASettings(BaseConfig):
    API_URL: str = os.getenv('NOPECHA_API_URL')
    API_KEY: Optional[str] = os.getenv('NOPECHA_API_KEY', 'I-K1GYMX8RX1G4')
    AUTO_OPEN: bool = os.getenv('NOPECHA_AUTO_OPEN', 'False').lower() == 'true'
    PLUGIN_CFG_PATH: Optional[str] = os.getenv(
        'NOPECHA_CFG_PATH',
        str(Path(__file__).parent.parent.joinpath('plugins').joinpath('chromium_automation').joinpath('manifest.json'))
    )

    @staticmethod
    def to_string():
        return "URL={}, KEY={}, AUTO_OPEN={}, PLUGIN_CFG_PATH={}".format(
            NopeCHASettings.API_URL,
            NopeCHASettings.API_KEY[5] if NopeCHASettings.API_KEY else '',
            NopeCHASettings.AUTO_OPEN,
            NopeCHASettings.PLUGIN_CFG_PATH
        )


class BrowserSettings(BaseConfig):
    BROWSER_BINARY_PATH: Optional[str] = os.getenv('CHROME_BROWSER_PATH',
                                                "/usr/local/bin/chrome") if GeneralSettings.browser_driver_type() == BrowserDriverType.Chrome else os.getenv(
        'FIREFOX_BROWSER_PATH', "/usr/local/bin/firefox")
    DRIVER_BINARY_PATH = os.getenv('CHROME_DRIVER_PATH',
                                   "/usr/local/bin/chromedriver") if GeneralSettings.browser_driver_type() == BrowserDriverType.Chrome else os.getenv(
        'FIREFOX_DRIVER_PATH', "/usr/local/bin/geckodriver")

    CHROME_UNDETECTED = False if not os.getenv('CHROME_BROWSER_UNDETECTED') else os.getenv(
        'CHROME_BROWSER_UNDETECTED').lower() in ('true', '1', 't')
    CHROME_INCOGNITO = False if not os.getenv('CHROME_BROWSER_INCOGNITO') else os.getenv(
        'CHROME_BROWSER_INCOGNITO').lower() in ('true', '1', 't')
    CHROME_HEADLESS = False if not os.getenv('CHROME_BROWSER_HEADLESS') else os.getenv(
        'CHROME_BROWSER_HEADLESS').lower() in ('true', '1', 't')
    FIREFOX_INCOGNITO = False if not os.getenv('FIREFOX_BROWSER_INCOGNITO') else os.getenv(
        'FIREFOX_BROWSER_INCOGNITO').lower() in ('true', '1', 't')
    FIREFOX_HEADLESS = False if not os.getenv('FIREFOX_BROWSER_HEADLESS') else os.getenv(
        'FIREFOX_BROWSER_HEADLESS').lower() in ('true', '1', 't')

    @staticmethod
    def to_string():
        return ("BROWSER_BINARY_PATH={}, DRIVER_BINARY_PATH={}, CHROME_UNDETECTED={}, CHROME_INCOGNITO={}, "
                "CHROME_HEADLESS={}, FIREFOX_INCOGNITO={}, FIREFOX_HEADLESS={}").format(
            BrowserSettings.BROWSER_BINARY_PATH, BrowserSettings.DRIVER_BINARY_PATH, BrowserSettings.CHROME_UNDETECTED,
            BrowserSettings.CHROME_INCOGNITO, BrowserSettings.CHROME_HEADLESS, BrowserSettings.FIREFOX_INCOGNITO,
            BrowserSettings.FIREFOX_HEADLESS)

class RedisSettings(BaseConfig):
    REDIS_HOST: Optional[str] = '127.0.0.1' if not os.getenv('REDIS_HOST') else os.getenv('REDIS_HOST')
    REDIS_PORT: Optional[int] = 6379 if not os.getenv('REDIS_PORT') else int(os.getenv('REDIS_PORT'))

    @staticmethod
    def rds() -> redis.client.Redis:
        return redis.Redis(host=RedisSettings.REDIS_HOST, port=RedisSettings.REDIS_PORT)

    @staticmethod
    def to_string():
        return "HOST={}, PORT={}".format(RedisSettings.REDIS_HOST, RedisSettings.REDIS_PORT)

class APISettings(BaseConfig):
    # Stores external URL to the API
    EXTERNAL_API_URL: Optional[str] = os.getenv('API_URL', 'http://localhost:8080')
    SERVER_HOST: Optional[str] = os.getenv('SERVER_HOST', 'localhost')
    SERVER_PORT: Optional[str] = os.getenv('SERVER_PORT', '8080')
    SCHEMA: Optional[str] = os.getenv('SERVER_SCHEMA', 'http')

    @staticmethod
    def url(external: bool = False) -> str:
        if external is True and APISettings.EXTERNAL_API_URL != '':
            return APISettings.EXTERNAL_API_URL

        return f'{APISettings.SCHEMA}://{APISettings.SERVER_HOST}:{APISettings.SERVER_PORT}'

    @staticmethod
    def to_string():
        return ("EXTERNAL_API_URL={}, "
                "HOST={}, PORT={}, SCHEMA={}").format(APISettings.EXTERNAL_API_URL, APISettings.SERVER_HOST,
                                                      APISettings.SERVER_PORT, APISettings.SCHEMA)


class ProxySettings(BaseConfig):
    PROTOCOL: str = 'https' if not os.getenv('PROXY_PROTOCOL') else os.getenv('PROXY_PROTOCOL')
    HOSTNAME: str = 'us-pr.oxylabs.io' if not os.getenv('PROXY_HOSTNAME') else os.getenv('PROXY_HOSTNAME')
    USERNAME: str = '' if not os.getenv('PROXY_USERNAME') else os.getenv('PROXY_USERNAME')
    PASSWORD: str = '' if not os.getenv('PROXY_PASSWORD') else os.getenv('PROXY_PASSWORD')
    DEFAULT_PROXY_DOMAINS = '' if not os.getenv('DEFAULT_PROXY_DOMAINS') else os.getenv('DEFAULT_PROXY_DOMAINS')
    PROXY_VARIATION: Optional[str] = 'INCLUSIVE' if not os.getenv('PROXY_VARIATION') else os.getenv('PROXY_VARIATION')
    PROXIED_IP_SERVICE_URL = APISettings.url(True) + '/my_ip' if not os.getenv(
        'PROXIED_IP_SERVICE_URL') else os.getenv('PROXIED_IP_SERVICE_URL')
    UNPROXIED_IP_SERVICE_URL = APISettings.url(False) + '/my_ip' if not os.getenv(
        'UNPROXIED_IP_SERVICE_URL') else os.getenv('UNPROXIED_IP_SERVICE_URL')
    MIN_RECAPTCHA_SCORE: int = int(os.getenv('MIN_RECAPTCHA_SCORE', '-1'))

    @staticmethod
    def to_string():
        return ("PROTOCOL={}, HOSTNAME={}, USERNAME={}, PASSWORD={}, DEFAULT_PROXY_DOMAINS={}, PROXY_VARIATION={}, "
                "PROXIED_URL={}, UNPROXIED_URL={}").format(
                    ProxySettings.PROTOCOL, ProxySettings.HOSTNAME,
                    ProxySettings.USERNAME,
                    ProxySettings.PASSWORD[3] if ProxySettings.PASSWORD else '',
                    ProxySettings.DEFAULT_PROXY_DOMAINS,
                    ProxySettings.PROXY_VARIATION,
                    ProxySettings.PROXIED_IP_SERVICE_URL,
                    ProxySettings.UNPROXIED_IP_SERVICE_URL
                )

class CacheSettings(BaseConfig):
    DOWNLOADS_PATH = '/var/tmp/cache' if not os.getenv('DOWNLOADS_PATH') else os.getenv('DOWNLOADS_PATH')
    BROWSER_PATH: Optional[str] = os.path.join(DOWNLOADS_PATH, '.browser') if not os.getenv(
        'CACHE_BROWSER_PATH') else os.path.join(DOWNLOADS_PATH, os.getenv('CACHE_BROWSER_PATH'))
    DATA_PATH: Optional[str] = os.path.join(DOWNLOADS_PATH, '.data') if not os.getenv('CACHE_DATA_PATH') else os.path.join(
        DOWNLOADS_PATH, os.getenv('CACHE_DATA_PATH'))
    DISK_PATH: Optional[str] = os.path.join(DOWNLOADS_PATH, '.disk') if not os.getenv('CACHE_DISK_PATH') else os.path.join(
        DOWNLOADS_PATH, os.getenv('CACHE_DISK_PATH'))
    GLOBALCACHE_PATH: Optional[str] = os.path.join(DOWNLOADS_PATH, '.globalcache') if not os.getenv(
        'CACHE_GLOBALCACHE_PATH') else os.path.join(DOWNLOADS_PATH, os.getenv('CACHE_GLOBALCACHE_PATH'))
    CACHE_USE = False if not os.getenv('CACHE_USE') else os.getenv('CACHE_USE', 'False').lower() in ('true', '1', 't')

    @staticmethod
    def to_string():
        return ("DOWNLOADS_PATH={}, BROWSER_PATH={}, DATA_PATH={}, DISK_PATH={}, GLOBALCACHE_PATH={}, "
                "CACHE_USE={}").format(
                    CacheSettings.DOWNLOADS_PATH, 
                    CacheSettings.BROWSER_PATH,
                    CacheSettings.DATA_PATH,
                    CacheSettings.DISK_PATH, 
                    CacheSettings.GLOBALCACHE_PATH, 
                    CacheSettings.CACHE_USE
                )

class ExtensionSettings(BaseConfig):
    PYPASSER_PLUGIN_CONFIG_PATH: Optional[str] = os.getenv(
        'PYPASSER_PLUGIN_CONFIG_PATH',
        str(Path(__file__).parent.parent.joinpath('plugins').joinpath('pypasser_plugin').joinpath('config.json'))
    )
    CHROME_PROXY_PLUGIN_CONFIG_PATH: Optional[str] = os.getenv(
        'PYPASSER_PLUGIN_CONFIG_PATH',
        str(Path(__file__).parent.parent.joinpath('plugins').joinpath('chrome_proxy_auth_plugin').joinpath(
            'background.js'))
    )

class AirnoiseSettings(BaseConfig):
    SUBMISSION_VERIFIER_API_KEY: str = os.getenv('SUBMISSION_VERIFIER_API_KEY', '')
    
    @staticmethod
    def to_string():
        return "SUBMISSION_VERIFIER_API_KEY={}".format(
            AirnoiseSettings.SUBMISSION_VERIFIER_API_KEY
        )