import logging
import os
import random
import shutil
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from zipfile import is_zipfile

import undetected_chromedriver as uc
from redis import Redis
from selenium.webdriver import ChromeOptions, FirefoxOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import SB
from urllib3.exceptions import MaxRetryError

from selenium.webdriver.remote.webelement import WebElement
from selenium_worker import config as cfg
from selenium_worker.Requests.MontgomeryCountyAirParkTaskRQ import MontgomeryCountyAirParkTaskRQ
from selenium_worker.Requests.WorkTaskRQ import WorkTaskRQ
from selenium_worker.Responses.WorkTaskRS import WorkTaskRS
from selenium_worker.enums import BrowserDriverType
from selenium_worker.utils import get_actual_ip_address, get_proxied_ip_address

logger = logging.getLogger(__name__)

# Human-like typing delay constants (seconds)
TYPING_DELAY_FROM = 0.05
TYPING_DELAY_TO = 0.20

# Proxy change wait time constants (seconds)
PROXY_CHANGE_WAIT_LOWER_BOUND = 0.25
PROXY_CHANGE_WAIT_UPPER_BOUND = 1.25

minimum_recaptcha_scores = {
    MontgomeryCountyAirParkTaskRQ: 3
}

from selenium_worker.utils import check_recaptcha_score


@dataclass
class PageSetupConfig:
    """Configuration class for tearup and teardown page setup operations."""
    initial_url: str
    downloads_path: str
    attempts: int = 3
    print_ip_addresses: bool = True
    max_attempts: int = 10
    recaptcha_score_threshold: int = 7
    proxy_variation: Optional[str] = None
    rds: Optional[Redis] = None


class TaskService:
    RQ: WorkTaskRQ
    RS: WorkTaskRS
    _sb_gen = None
    SB = None
    driver = None
    user_data_dir: str = ''

    def __init__(self):
        self.RQ = WorkTaskRQ({})
        self.RS = WorkTaskRS()

    def shutdown(self, remove_user_data: bool = True):
        if self.SB:
            try:
                next(self._sb_gen)
                self._sb_gen = None
                self.SB = None
            except StopIteration:
                pass

        if remove_user_data and self.user_data_dir:
            try:
                shutil.rmtree(os.path.join(cfg.CacheSettings.DATA_PATH, self.user_data_dir), ignore_errors=True)
                self.log(f"User data directory deleted: {self.user_data_dir}")

            except Exception as e:
                self.log(f"Failed to remove user data directory '{self.user_data_dir}': {e}")

    def get_extensions(self, browser_driver_type: BrowserDriverType) -> list[str]:
        match browser_driver_type:
            case BrowserDriverType.Chrome:
                return ["chrome_proxy_auth_plugin", "pypasser_plugin", "chromium_automation"]

        return list[str]()

    def get_driver_options(self, browser_driver_type: BrowserDriverType, extensions: list) -> ChromeOptions:
        driver_options = None
        match browser_driver_type:
            case BrowserDriverType.Chrome:
                if cfg.BrowserSettings.CHROME_UNDETECTED:
                    driver_options = uc.ChromeOptions()
                else:
                    driver_options = ChromeOptions()

                driver_options.add_argument('--disable-blink-features=AutomationControlled')
                driver_options.add_argument('--disable-dev-shm-usage')
                # driver_options.add_argument('--no-sandbox') # appears to be unsupported now
                driver_options.add_argument('--force-fieldtrials=AutomaticTabDiscarding/Disabled')
                driver_options.add_argument('--disable-browser-side-navigation')
                driver_options.accept_insecure_certs = True

                if cfg.BrowserSettings.CHROME_HEADLESS:
                    driver_options.add_argument('--headless=new')
                if cfg.BrowserSettings.CHROME_INCOGNITO:
                    driver_options.add_argument('--incognito')

        return driver_options

    def load_extensions(self, browser_driver_type: BrowserDriverType, driver_options: ChromeOptions | FirefoxOptions,
                        extensions: list[str]) -> ChromeOptions | FirefoxOptions | None:
        if len(extensions) == 0:
            return driver_options

        match browser_driver_type:
            case BrowserDriverType.Chrome:
                extensions_list = []
                for extension in extensions:
                    extensions_list.append(os.path.abspath(os.path.join("plugins", extension)))

                driver_options.add_argument(f'--load-extension=' + ','.join(extensions_list))

        return driver_options

    def create_driver(self, browser_driver_type: BrowserDriverType,
                      browser_binary_path: str = None, user_data_dir: str = None,
                      browser_data_dir: str = None, disk_cache_dir: str = None
                      ):
        if self.driver is not None:
            self.shutdown()
        # after shutdown() the user_data_dir became empty
        self.user_data_dir = user_data_dir

        logger.info(f'Creating a browser with {browser_driver_type}')
        extensions = self.get_extensions(browser_driver_type)
        driver_options = self.get_driver_options(browser_driver_type, extensions)

        if browser_driver_type is BrowserDriverType.Chrome:
            if self.user_data_dir is not None:
                driver_options.add_argument(f"--user-data-dir={self.user_data_dir}")
            if browser_data_dir is not None:
                driver_options.add_argument(f"--data-path={browser_data_dir}")
            if disk_cache_dir is not None:
                driver_options.add_argument(f"--disk-cache-dir={disk_cache_dir}")
            if browser_binary_path is not None:
                driver_options.binary_location = browser_binary_path

        match browser_driver_type:
            case BrowserDriverType.Chrome:
                extensions_list = []
                for extension in extensions:
                    extensions_list.append(os.path.abspath(os.path.join("plugins", extension)))

                driver_options.add_argument('--disable-infobars')
                self._sb_gen = SB(browser='chrome', uc=cfg.BrowserSettings.CHROME_UNDETECTED,
                                  incognito=cfg.BrowserSettings.CHROME_INCOGNITO, window_size="1920, 1080",
                                  position="0, 0", extension_dir=','.join(extensions_list),
                                  headless=cfg.BrowserSettings.CHROME_HEADLESS,
                                  test=False, chromium_arg=','.join(driver_options.arguments)).gen
                self.SB = next(self._sb_gen)
                self.driver = self.SB.driver

        if self.driver is None:
            raise RuntimeError('Cannot find any browser driver')
        logger.info(f'Browser {browser_driver_type} was created successfully')

    def init_browser(self, browser_driver_type: BrowserDriverType, task_type: str):
        logger.info('Initializing browser ...')
        self.user_data_dir = os.path.join(cfg.CacheSettings.DATA_PATH, uuid4().__str__())
        logger.info(f'User data directory is {self.user_data_dir}')
        if browser_driver_type == BrowserDriverType.Chrome and os.path.exists(
                os.path.join(cfg.CacheSettings.GLOBALCACHE_PATH,
                             f'{task_type}.zip')) and cfg.CacheSettings.CACHE_USE is True:  # Check before copying
            # Copy from global cache into user data
            if is_zipfile(os.path.join(cfg.CacheSettings.GLOBALCACHE_PATH, f'{task_type}.zip')):
                try:
                    logger.info('Unpacking archive ' + os.path.join(cfg.CacheSettings.GLOBALCACHE_PATH,
                                                              f'{task_type}.zip') + f' into {self.user_data_dir}')
                    shutil.unpack_archive(os.path.join(cfg.CacheSettings.GLOBALCACHE_PATH, f'{task_type}.zip'),
                                          self.user_data_dir)
                except Exception as e:
                    logger.error(f"{e}")
            else:
                logger.info(f"Skipping using cache from ZIP file {task_type}.zip")

        self.create_driver(browser_driver_type,
                           browser_binary_path=cfg.BrowserSettings.BROWSER_BINARY_PATH,
                           user_data_dir=self.user_data_dir,  # This is browser profile path
                           browser_data_dir=cfg.CacheSettings.BROWSER_PATH,
                           disk_cache_dir=cfg.CacheSettings.DISK_PATH
                           )

        try:
            self.driver.delete_all_cookies()
        except BaseException as e:
            self.log('Failed to cleanup cookies after browser start-up: ' + str(e))
            self.RS.Body = self.driver.page_source

        return self.user_data_dir

    # Prepare the state page before submitting form data with ID/DL data
    def tearup(self, config: PageSetupConfig) -> list[str]:
        """
        Prepare the state page before submitting form data with ID/DL data.

        Args:
            config: Configuration object containing all setup parameters

        Returns:
            List of log messages from the response
        """
        self.log(f'Obtaining the page with URL {config.initial_url}')
        self.driver.get(config.initial_url)
        self.log(f'Waiting for {config.initial_url} to load ...')

        while True:
            try:
                ready_state = self.driver.execute_script('return document.readyState')
                logger.debug(f'document.readyState: {ready_state}')
                if ready_state in ['loading', 'interactive', 'complete']:
                    logger.debug('Page started loading')
                    break
            except Exception:
                pass
            time.sleep(0.1)
        self.log(f'Page {config.initial_url} has loaded')
        return self.RS.Logs

    # Prepare the state page after ID/DL data was obtained
    def teardown(self, config: PageSetupConfig) -> list[str]:
        """
        Prepare the state page after ID/DL data was obtained.

        Args:
            config: Configuration object containing all setup parameters

        Returns:
            List of log messages from the response
        """
        logs = list[str]()
        logs.append(f'Obtaining the page with URL {config.initial_url}')
        self.driver.get(config.initial_url)

        logs.append(f'Waiting for {config.initial_url} to load ...')

        while True:
            try:
                ready_state = self.driver.execute_script('return document.readyState')
                logger.debug(f'document.readyState: {ready_state}')
                if ready_state in ['loading', 'interactive', 'complete']:
                    logger.debug('Page started loading')
                    break
            except Exception:
                pass
            time.sleep(0.1)
        logs.append(f'Page {config.initial_url} has loaded')
        return logs

    # Enters the data and obtains driver license validation results
    def process(self, initial_url: str, downloads_path: str) -> WorkTaskRS:
        response = WorkTaskRS()
        response.Error = "Not Implemented"
        return response

    # Enters the data and prepares the state for data processing
    def prepare(self, initial_url: str, downloads_path: str) -> WorkTaskRS:
        response = WorkTaskRS()
        response.Error = "Not Implemented"
        return response

    # Load a page with a timeout
    def load_page(self, initial_url: str, timeout_in_ms: int) -> WorkTaskRS:
        try:
            if timeout_in_ms > 0:
                self.driver.set_page_load_timeout(timeout_in_ms / 1000)
            self.log(f'Obtaining page URL of {initial_url} for {self.__class__.__name__}')
            self.driver.get(initial_url)
        except BaseException as e:
            self.log(f'Failed to load the page URL {initial_url}: ' + str(e))
            self.RS.Body = self.driver.page_source

        return self.RS

    def wait_for_page_to_load(self, timeout_in_ms: int = 5000) -> WorkTaskRS:
        try:
            self.RS.Body = self.driver.page_source
            if timeout_in_ms > 0:
                self.driver.set_page_load_timeout(timeout_in_ms / 1000)
            while self.driver.execute_script("return document.readyState") != "complete":
                pass
        except BaseException as e:
            self.log(f'Failed to load the page within timeout of {timeout_in_ms} ms.: ' + str(e))
            self.RS.Body = self.driver.page_source

        return self.RS

    # Wait for element to appear on the page and be clickable, with the timeout
    def wait_for_element_to_be_clickable(self, element: str, selector: str,
                                         timeout_in_ms: int = 5000) -> WorkTaskRS:
        if timeout_in_ms == 0:
            return self.RS

        wait_timeout = WebDriverWait(self.driver, timeout_in_ms / 1000, poll_frequency=0.5)
        try:
            wait_timeout.until(EC.element_to_be_clickable((selector, element)))
        except BaseException as e:
            self.log(f'Failed to locate element {element} on the page in {timeout_in_ms} ms. timeout: ' + str(e))
            self.RS.Body = self.driver.page_source

        return self.RS

    # Wait for element to appear on the page, with the timeout
    def wait_for_element_to_appear(self, element: str, selector: str,
                                   timeout_in_ms: int = 5000) -> WorkTaskRS:
        if timeout_in_ms == 0:
            return self.RS

        wait_timeout = WebDriverWait(self.driver, timeout_in_ms / 1000, poll_frequency=0.5)
        try:
            wait_timeout.until(EC.visibility_of_element_located((selector, element)))
        except BaseException as e:
            self.log(f'Failed to locate element {element} on the page in {timeout_in_ms} ms. timeout: ' + str(e))
            self.RS.Body = self.driver.page_source

        return self.RS

    def change_proxy_repeat(self, 
            print_ip_addresses: bool = True, 
            max_attempts: int = 10,
            recaptcha_score_threshold: int = 7, 
            proxy_variation: Optional[str] = None):
        logger.info('Attempting to find a proxy with reCAPTCHA score >= {}'.format(recaptcha_score_threshold))
        
        for attempt in range(max_attempts):
            try:
                self.change_proxy(print_ip_addresses, proxy_variation, recaptcha_score_threshold)
                if recaptcha_score_threshold == 0:
                    return ''

                time.sleep(random.uniform(PROXY_CHANGE_WAIT_LOWER_BOUND, PROXY_CHANGE_WAIT_UPPER_BOUND))
                recaptcha_score = check_recaptcha_score(self.driver)
                if recaptcha_score >= recaptcha_score_threshold:
                    self.log('Recaptcha proxy score obtained: {} above or equal to {} '.format(str(recaptcha_score),
                                                                                               str(recaptcha_score_threshold)))
                    return ''
            except MaxRetryError as mre:
                self.error('Failed to change proxy due to error: ' + str(mre))
                continue
            except BaseException as e:
                self.error('Failed to change proxy due to exception: ' + str(e))
                continue

        return 'Failed to find a suitable proxy for worker with UID of'.format(cfg.GeneralSettings.WORKER_UID)

    def change_proxy(self, 
            print_ip_addresses: bool = True, 
            proxy_variation: Optional[str] = None,
            min_score: int = 3, 
            max_score: int = 10) -> Optional[str]:
        changed = ''
        if proxy_variation is None or proxy_variation == '':
            proxy_variation = cfg.ProxySettings.PROXY_VARIATION

        if self.driver.name == 'chrome':
            try:
                query_args = {
                    "worker_uid": cfg.GeneralSettings.WORKER_UID,
                    "proxy_host": cfg.ProxySettings.HOSTNAME, "proxy_protocol": cfg.ProxySettings.PROTOCOL,
                    "proxy_username": cfg.ProxySettings.USERNAME, "proxy_password": cfg.ProxySettings.PASSWORD,
                    "proxy_domains": cfg.ProxySettings.DEFAULT_PROXY_DOMAINS,
                    "proxy_variation": proxy_variation, "api_url": cfg.APISettings.url(True), "min_score": min_score,
                    "max_score": max_score
                }
                # Create a copy of query_args with sensitive data redacted for logging
                redacted_query_args = query_args.copy()
                redacted_query_args["proxy_username"] = "REDACTED"
                redacted_query_args["proxy_password"] = "REDACTED"
                logger.info(
                    'Making request to ' + f'{cfg.APISettings.url()}/get_proxy_details_fake?' + urllib.parse.urlencode(
                        redacted_query_args))
                self.driver.get(
                    f'{cfg.APISettings.url()}/get_proxy_details_fake?' + urllib.parse.urlencode(query_args))
                self.log(f'Proxy change request is completed')
            except BaseException as e:
                changed = 'Failed to change proxy: ' + str(e)
                self.error(f'Error during proxy change for worker UID of {cfg.GeneralSettings.WORKER_UID}: ' + str(e))
            finally:
                pass

        if 'The proxy server is refusing connections' in self.driver.page_source:
            return 'The proxy server is refusing connections'

        if print_ip_addresses:
            time.sleep(0.5)
            try:
                actual_ip_address = get_actual_ip_address()
                logger.info('Actual IP address: {}'.format(actual_ip_address))
            except Exception as e:
                logger.warning('Failed to obtain actual IP address: {}'.format(e))
            try:
                # For proxy change obtain it via Selenium because request-based will obtain it from Redis
                proxied_ip_address = get_proxied_ip_address(self.driver)
                logger.info('Proxied IP address: {}'.format(proxied_ip_address))
            except Exception as e:
                logger.warning('Failed to obtain proxied IP address: {}'.format(e))

        return changed

    def get_prepare_block_urls(self):
        return []

    def get_process_block_urls(self):
        return []

    def log(self, logs: str):
        log_message = f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S.%f")[:-3]}] - {logs}'
        logger.info(log_message)
        self.RS.Logs.append(log_message)

    def error(self, logs: str):
        log_message = f'[{datetime.now(timezone.utc).strftime("%Y-%m-%d-%H:%M:%S.%f")[:-3]}] - {logs}'
        logger.error(log_message)
        self.RS.Logs.append(log_message)
        self.RS.Error = log_message

    def human_like_typing(self,
            element: WebElement,
            text: str,
            delay_from: float = TYPING_DELAY_FROM,
            delay_to: float = TYPING_DELAY_TO):
        for char in text:
            time.sleep(random.uniform(delay_from, delay_to))
            element.send_keys(char)

    def find_and_verify_element(self, locator_type, locator_value: str, field_name: str) -> WebElement:
        """
        Verify an element is visible and find it.

        Args:
            locator_type: The type of locator (e.g., By.ID, By.CLASS_NAME)
            locator_value: The value of the locator
            field_name: Human-readable name for the field (used in error messages)

        Returns:
            WebElement: The found element

        Raises:
            Exception: If element is not visible or cannot be found
        """
        try:
            if EC.visibility_of_element_located((locator_type, locator_value)):
                element = self.SB.find_element(locator_type, locator_value)
                return element
            else:
                raise Exception(f'{field_name} field is not visible')
        except BaseException as ex:
            self.error(f'Failed to find {field_name} field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            raise ex

    def scroll_and_interact_with_element(self, element: WebElement, field_name: str):
        """
        Scroll element into view, move to it, and click it.

        Args:
            element: The WebElement to interact with
            field_name: Human-readable name for the field (used in error messages)

        Raises:
            Exception: If interaction fails
        """
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            actions = ActionChains(self.driver)
            actions.move_to_element(element)
            actions.click()
            actions.perform()
        except BaseException as ex:
            self.error(f'Failed to scroll and interact with {field_name} field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            raise ex

    def fill_form_field(self, locator_type, locator_value: str, field_name: str, text_value: str):
        """
        Complete form field interaction: find, verify, scroll, click, and type.

        Args:
            locator_type: The type of locator (e.g., By.ID, By.CLASS_NAME)
            locator_value: The value of the locator
            field_name: Human-readable name for the field (used in error messages)
            text_value: The text to type into the field

        Raises:
            Exception: If any step of the interaction fails
        """
        try:
            element = self.find_and_verify_element(locator_type, locator_value, field_name)
            self.scroll_and_interact_with_element(element, field_name)
            self.human_like_typing(element, text_value)

        except BaseException as ex:
            self.error(f'Failed to fill {field_name} field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            raise ex

