import json
import os
import platform
import random
import re
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, date
from typing import TYPE_CHECKING, List, Optional
from urllib.parse import quote_plus

import requests
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver

from selenium_worker import config as cfg
from selenium_worker.enums import BrowserDriverType

if TYPE_CHECKING:
    pass


def date_parser(dct):
    for key, value in dct.items():
        if isinstance(value, str):
            try:
                dct[key] = datetime.fromisoformat(value)
            except ValueError:
                pass
    return dct


def date_encoder(obj):
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See https://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def build_pypasser_config_json():
    config_file_path = cfg.ExtensionSettings.PYPASSER_PLUGIN_CONFIG_PATH

    if not os.path.exists(config_file_path):
        print('PyPasser extension config file not found')
        return

    with open(config_file_path, 'r') as config_file:
        config = json.load(config_file)

    config['backend_url'] = cfg.APISettings.url()

    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file, indent=4)
    print(f"PyPasser extension config file written to {config_file_path}.\nAPI url: {cfg.APISettings.url()}")


def check_my_ip_address(driver: Driver):
    original_window = driver.current_window_handle

    driver.execute_script("window.open('');")
    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

    new_window = [window for window in driver.window_handles if window != original_window][0]
    driver.switch_to.window(new_window)

    driver.get("https://whatismyipaddress.com/")

    try:
        ip_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#ipv4 > a"))
        )
        print(f"Currently IP: {ip_element.text}")
    except Exception as e:
        print(f"Failed to get IP address: {e}")

    driver.close()
    driver.switch_to.window(original_window)


def build_nopecha_config():
    config_file_path = cfg.NopeCHASettings.PLUGIN_CFG_PATH

    if not os.path.exists(config_file_path):
        print('Extension config file not found')
        return

    with open(config_file_path, 'r') as config_file:
        config = json.load(config_file)

    config['nopecha']['key'] = cfg.NopeCHASettings.API_KEY
    config['nopecha']['recaptcha_auto_open'] = cfg.NopeCHASettings.AUTO_OPEN

    with open(config_file_path, 'w') as config_file:
        json.dump(config, config_file, indent=4)
    print(f"Extension config file written to {config_file_path}.\nAutoOpen: {cfg.NopeCHASettings.AUTO_OPEN}")


# Archives specified directory and returns full path to archived file
def archive_user_data(state_iin: int, browser_driver_type: BrowserDriverType, user_data_dir: str) -> str:
    # Pre-copy user data directory into temporary one
    with tempfile.TemporaryDirectory() as tmp_state_dir:
        print(f'Created temporary directory {tmp_state_dir} for user data')
        # Copy latest cache into it
        try:
            print(f'Begin copying data from user data directory {user_data_dir} to temporary directory {tmp_state_dir}')
            shutil.copytree(user_data_dir, tmp_state_dir, dirs_exist_ok=True, ignore_dangling_symlinks=True,
                            ignore=shutil.ignore_patterns('SingletonCookie', 'SingletonLock', 'SingletonSocket',
                                                          'RunningChromeVersion'))
            print('Copied user data into temporary directory')
        except Exception as e:
            print('Failed to copy user data into temporary directory: {}'.format(e))
            return ''

        match browser_driver_type:
            case BrowserDriverType.Chrome:
                print(f'Creating {state_iin}.zip user data archive')
                full_archive_path = zip_directory(tmp_state_dir, f'{state_iin}.zip')
                if full_archive_path is None or full_archive_path == '':
                    raise Exception('Failed to create ZIP archive')
                print(f'Created {full_archive_path} file successfully')
                return full_archive_path
            case BrowserDriverType.Firefox:
                return ''
        return ''


def time_diff_ms(date1: datetime, date2: datetime) -> int:
    return round((date1 - date2).total_seconds() * 1000 + (date1 - date2).microseconds / 1000)


def get_proxied_ip_address(driver: Driver) -> str:
    driver.get(cfg.ProxySettings.PROXIED_IP_SERVICE_URL)
    matches = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", driver.page_source)
    if len(matches) > 0:
        return matches[0]

    return ''


def check_recaptcha_score(driver: Driver) -> int:
    driver.get('https://antcpt.com/score_detector/')
    for wait in range(1, 10):
        results = re.findall(r'Your score is: (\d\.\d)', driver.page_source)
        if len(results) == 0:
            time.sleep(1.0)
        else:
            break

    results = re.findall(r'Your score is: (\d\.\d)', driver.page_source)
    if len(results) == 0:
        score = 0
    else:
        score = int(float(results[0]) * 10)

    print('Your score is: {}'.format(score))

    try:
        cookies = driver.execute_cdp_cmd("Network.getAllCookies",
                                         {"urls": ["https://antcpt.com", "https://www.google.com"]})
        for cookie in cookies['cookies']:
            if cookie['name'] == '_GRECAPTCHA':
                driver.execute_cdp_cmd('Network.deleteCookies', {"name": cookie['name'], "domain": cookie['domain']})
    except Exception as e:
        print('Failed to get or delete cookie _GRECAPTCHA: {}'.format(e))
        pass

    return score


def get_actual_ip_address() -> str:
    request_session = requests.Session()
    own_ip_response = request_session.get(cfg.ProxySettings.UNPROXIED_IP_SERVICE_URL)
    if own_ip_response.status_code != 200:
        raise Exception('Failed to get own IP address: {}'.format(own_ip_response.text))

    ip_address_match = re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", own_ip_response.text)
    if ip_address_match is not None:
        return str(ip_address_match[0])

    return ''


def search_in_duckduck(driver, request_to_find: List[str]) -> bool:
    actions = ActionChains(driver)

    for item_to_search in request_to_find:
        try:
            driver.get('https://duckduckgo.com/')
            time.sleep(1)

            search_input = driver.find_element(By.CSS_SELECTOR, '#searchbox_input')
            search_input.click()
            search_input.clear()
            (
                actions
                .send_keys(item_to_search)
                .send_keys(Keys.ENTER)
                .perform()
            )

            time.sleep(1)

            result_links = driver.find_elements(By.CSS_SELECTOR, 'section > ol > li a')
            top_links = result_links[4:8]

            if not top_links:
                print(f'No results found for: {item_to_search}')
                continue

            random.choice(top_links).click()
            time.sleep(1)
            driver.execute_script("window.scrollBy({top: 400, left: 0, behavior: 'smooth'});")

        except Exception as e:
            print(f'Failed to process "{item_to_search}" in DuckDuckGo: {e}')
            continue

    return True


def google_search(driver, request_to_find: List[str], timeout_in_ms: int = 5000) -> bool:
    from selenium_worker.pypasser.reCaptchaV2 import UnifiedCaptchaV2Solver
    for index, query in enumerate(request_to_find):
        print('Searching ({} out of {}) for: "{}"'.format(index + 1, len(request_to_find), query))
        try:
            encoded_query = quote_plus(query)
            driver.get(f'https://www.google.com/search?q={encoded_query}')

            if UnifiedCaptchaV2Solver.captcha_is_visible_on_page(driver, 5, 1):
                UnifiedCaptchaV2Solver.__click_check_box__(driver)
                UnifiedCaptchaV2Solver.__check_checkbox_is_checked__(driver)

            if timeout_in_ms > 0:
                driver.set_page_load_timeout(timeout_in_ms / 1000)
            while driver.execute_script("return document.readyState") != "complete":
                pass

            time.sleep(0.1)

        except Exception as e:
            print(f'Failed to process "{query}" in Google: {e}')
            continue

    return True


def zip_directory(folder_path: str, zip_file_path: str) -> str:
    with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED, strict_timestamps=False) as zf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                archive_path = os.path.relpath(file_path, folder_path)
                zf.write(file_path, arcname=archive_path)

    return zip_file_path

def get_date(date_str: str, date_formats=None) -> Optional[datetime]:
    if date_formats is None:
        date_formats = ['%m%d%Y', '%m-%d-%Y', '%m/%d/%Y']
    dates = []
    first_digits = date_str[:2]
    if first_digits.isdigit() and int(first_digits) > 12:
        date_formats.extend(['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d'])
    for date_format in date_formats:
        try:
            date = datetime.strptime(date_str, date_format)
            dates.append(date)
        except ValueError:
            pass

    dates = [date for date in dates if str(date.year) in date_str or date.year < 1900]
    dates.sort(key=lambda x: x.year)

    if len(dates) > 1:
        return None
    elif len(dates) == 0:
        return None
    else:
        return dates[0]

