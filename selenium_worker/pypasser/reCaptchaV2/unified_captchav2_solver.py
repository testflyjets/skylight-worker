import os
import random
import time
import traceback
import uuid
from typing import List
from urllib.parse import urlparse

import keyboard as kb
import requests
import speech_recognition as sr
from pydub import AudioSegment
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from seleniumbase import Driver

from selenium_worker import config as cfg
from selenium_worker.pypasser.exceptions import IpBlock

__all__ = ["UnifiedCaptchaV2Solver"]


class UnifiedCaptchaV2Solver:
    """
    UnifiedCaptchaV2Solver bypass
    -----------------
    Solving reCaptcha V2 using speech to text

    Attributes
    ----------
    driver: webdriver

    play: bool
        default is True

    attempts: int
        default is 3 times

    Returns
    ----------
    bool: result of solver
    """

    def __new__(cls, *args, **kwargs) -> bool:
        instance = super(UnifiedCaptchaV2Solver, cls).__new__(cls)
        instance.__init__(*args, **kwargs)

        file_path = None
        wav_file_path = None

        try:
            cls.__click_check_box__(instance.driver)
            instance.driver.switch_to.default_content()

            time.sleep(1)
            if cls.__is_checked__(instance.driver):
                print("checked")
                return True
            else:
                print("not checked")

                instance.driver.switch_to.default_content()

                cls.__click_audio_button__(instance.driver)
                print("clicked audio")

                cls.__get_redis_key_and_paste__(instance.driver)
                return True


        except NoSuchElementException as e:
            print(e)
            return True
        except Exception as e:
            print(e)
            if 'rc-doscaptcha-header' in instance.driver.page_source:
                raise IpBlock()
            else:
                raise e
        finally:
            files_path_to_delete = list(filter(None, [file_path, wav_file_path]))
            cls.delete_temp_files(files_path_to_delete)

    def __init__(
            self,
            driver: Driver,
            play: bool = True,
            attempts: int = 3,
            downloads_path: str = '',
            need_to_solve: bool=True,
            need_to_reload_captcha_frame: bool=False
    ):
        self.driver = driver
        self.play = play
        self.attempts = attempts
        self.downloads_path = downloads_path

    @staticmethod
    def __click_check_box__(driver: Driver):
        iframes = driver.find_elements(By.XPATH, "//iframe")
        for index, iframe in enumerate(iframes):
            # Your sweet business logic applied to iframe goes here.
            try:
                driver.switch_to.frame(iframe)
            except Exception as e:
                pass
            recaptcha_anchor = driver.find_elements(By.ID, "recaptcha-anchor")
            if len(recaptcha_anchor) != 0:
                recaptcha_anchor[0].click()
                print("checkbox clicked")
                return True
            UnifiedCaptchaV2Solver.__click_check_box__(driver)
        driver.switch_to.parent_frame()

    @staticmethod
    def __is_checked__(driver: Driver):
        iframes = driver.find_elements(By.XPATH, "//iframe")
        # print(requests.session().__dict__)
        for index, iframe in enumerate(iframes):
            # Your sweet business logic applied to iframe goes here.
            driver.switch_to.frame(iframe)
            is_checked_checkbox = driver.find_elements(By.CSS_SELECTOR, ".recaptcha-checkbox-checked")
            if len(is_checked_checkbox) != 0:
                return True
            return UnifiedCaptchaV2Solver.__is_checked__(driver)
        return False

    @staticmethod
    def __captcha_continue_button__(driver: Driver, download_button: bool):
        tab_count = 5 if download_button else 4

        print(f"has audio download button: {download_button}. Now tab count: {tab_count}")
        actions = ActionChains(driver)
        (
            actions
            .send_keys(Keys.TAB * tab_count)
            .send_keys(Keys.ENTER)

            .perform()
        )

    @staticmethod
    def __click_audio_button__(driver: Driver):
        actions = ActionChains(driver)
        (
            actions
            .send_keys(Keys.TAB)
            .send_keys(Keys.ENTER)

            .perform()
        )

    @staticmethod
    def __get_audio_link__(driver: Driver, play=None):

        iframes = driver.find_elements(By.XPATH, "//iframe")
        for index, iframe in enumerate(iframes):
            driver.switch_to.frame(iframe)
            audio_source = driver.find_elements(By.ID, "audio-source")
            if len(audio_source) != 0:
                if audio_source[0].tag_name == 'audio':
                    link = audio_source[0].get_attribute('src')
                else:
                    link = audio_source[0].get_attribute('href')
                return link
            return UnifiedCaptchaV2Solver.__get_audio_link__(driver)
        return

    @staticmethod
    def __paste_decoded_audio_text__(driver: Driver, text=None):
        actions = ActionChains(driver)
        (
            actions
            .send_keys(Keys.TAB)
            .send_keys(text)

            .perform()
        )

    @staticmethod
    def __type_text__(driver: Driver, text=None):
        iframes = driver.find_elements(By.XPATH, "//iframe")
        for index, iframe in enumerate(iframes):
            # Your sweet business logic applied to iframe goes here.
            driver.switch_to.frame(iframe)
            audio_response_field = driver.find_elements(By.CSS_SELECTOR, "#audio-response")
            if len(audio_response_field) != 0:
                audio_response_field[0].send_keys(text, Keys.ENTER)
                driver.switch_to.default_content()
                return True
            return UnifiedCaptchaV2Solver.__type_text__(driver)
        return False

    @staticmethod
    def __check_valid_captcha__(driver: Driver):
        iframes = driver.find_elements(By.XPATH, "//iframe")
        for index, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
            except Exception as e:
                print(f"cant switch to {iframe}: {e}")
            recaptcha_anchor = driver.find_elements(By.ID, "recaptcha-anchor")
            if len(recaptcha_anchor) != 0:
                correct_iframe = iframe
                driver.switch_to.default_content()
                UnifiedCaptchaV2Solver.__click_check_box__(driver)
                time.sleep(0.3)
                UnifiedCaptchaV2Solver.__click_audio_button__(driver)
                recaptcha_anchor[0].get_attribute('title')
                print("checkbox clicked")
                return True
            UnifiedCaptchaV2Solver.__check_valid_captcha__(driver)
        driver.switch_to.parent_frame()

    @staticmethod
    def speech_to_text(audio_path: str) -> str:
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)

        return r.recognize_sphinx(audio)

    @staticmethod
    def __speech_to_text_new__(link: str, file_path: str, wav_file_path: str) -> str:
        # download audio file
        response = requests.get(link)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        # convert to wav
        audio = AudioSegment.from_file(file_path)
        audio.export(wav_file_path, format="wav")

        # recognize speech
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data, language='en')
        except sr.UnknownValueError:
            print("Audio text conversion failed")
        except sr.RequestError as e:
            print(f"Error requesting results from Google API: {e}")
        else:
            return text

    @staticmethod
    def delete_temp_files(file_paths: List[str]):
        for file in file_paths:
            try:
                os.remove(file)
                print(f"Deleted temp file: {file}")
            except Exception as e:
                print(f"Error deleting temp {file}: {e}")

    @staticmethod
    def __check_checkbox_is_checked__(driver: Driver):
        page = driver.current_url
        max_attempts = 100
        attempt = 1

        while attempt <= max_attempts:
            driver.switch_to.default_content()

            if driver.current_url != page:
                driver.switch_to.default_content()
                print('page changed, skipped')
                return

            if UnifiedCaptchaV2Solver.__is_checked__(driver):
                driver.switch_to.default_content()
                print('Checkbox is checked, captcha solved')
                return

            print("Checkbox not checked, retrying...")
            time.sleep(2)

            if attempt % 3 == 0:
                try:
                    driver.switch_to.default_content()
                    UnifiedCaptchaV2Solver.__click_check_box__(driver)
                    driver.switch_to.default_content()

                except Exception:
                    print('Failed to click checkbox')

            attempt += 1

        print(f"Checkbox check exceeded {max_attempts} attempts.")

    @staticmethod
    def human_like_typing(text: str):
        for char in text:
            time.sleep(random.uniform(0.05, 0.1))
            kb.write(char)

        return

    @staticmethod
    def captcha_is_visible_on_page(driver, timeout: int = 20, count_of_iframes: int = 2):
        time.sleep(1)
        iframes = driver.find_elements(By.XPATH, "//iframe")
        if len(iframes) == 0:
            return False
        driver.switch_to.frame(iframes[0])
        end_time = time.time() + timeout

        while time.time() < end_time:
            iframes_inside = driver.find_elements(By.XPATH, "//iframe")
            time.sleep(0.2)

            if len(iframes_inside) >= count_of_iframes:
                driver.switch_to.default_content()
                return True

        driver.switch_to.default_content()
        return False

    @staticmethod
    def __get_redis_key_and_paste__(driver: Driver):
        parsed = urlparse(driver.current_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        key = None
        for i in range(25):
            try:
                key = cfg.RedisSettings.rds().get(f"audio_link_{domain}")
                if key is not None:
                    break
                time.sleep(0.2)
            except Exception as e:
                print(f"error getting redis key try again: {e}")
                print(traceback.format_exc())
                pass

        if not key:
            print(f"redis key not found")
            return False

        print(f"redis values: {key}")
        split_values_from_key = key.split()
        if not split_values_from_key or len(split_values_from_key) != 3:
            print("error getting info from redis")
            return False

        audio_link = split_values_from_key[0].decode("utf-8")
        has_audio_download_button = split_values_from_key[1].decode("utf-8") == "True"

        if not audio_link:
            print("no audio link")
            return False

        file_path = f"audio_{uuid.uuid4().hex}.mp3"
        wav_file_path = file_path.replace(".mp3", ".wav")
        decoded_text = UnifiedCaptchaV2Solver.__speech_to_text_new__(audio_link, file_path, wav_file_path)
        if decoded_text:
            time.sleep(0.4)
            UnifiedCaptchaV2Solver.__paste_decoded_audio_text__(driver, decoded_text)
            print("decoded audio text pasted")

        time.sleep(0.6)
        UnifiedCaptchaV2Solver.__captcha_continue_button__(driver, has_audio_download_button)
        print("clicked continue captcha button")
        driver.switch_to.default_content()

    @staticmethod
    def __check_valid_captcha__(driver: Driver) -> bool:
        parsed = urlparse(driver.current_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        key = None
        for _ in range(25):
            try:
                key = cfg.RedisSettings.rds().get(f"audio_link_{domain}")
                if key:
                    break
                time.sleep(0.2)
            except Exception as e:
                print(f"Error getting Redis key, trying again: {e}")
                print(traceback.format_exc())

        if not key:
            print("Redis key not found")
            return False

        # Декодируем значение (если Redis возвращает bytes)
        if isinstance(key, bytes):
            key = key.decode('utf-8')

        parts = key.split()
        if len(parts) > 1 and parts[1] == "False":
            return False

        return True