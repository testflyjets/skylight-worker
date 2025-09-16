import time
from typing import Optional

from redis import Redis
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium_worker.Requests.MontgomeryCountyAirParkTaskRQ import MontgomeryCountyAirParkTaskRQ
from selenium_worker.Responses.MontgomeryCountyAirParkTaskRS import MontgomeryCountyAirParkTaskRS
from selenium_worker.Services.TaskService import TaskService
from selenium_worker.constants import STAGE_OBTAINED_PAGE
from selenium_worker.exceptions import RetryException
from selenium_worker.utils import get_date


class MontgomeryCountyAirParkTask(TaskService):
    RQ: MontgomeryCountyAirParkTaskRQ
    RS: MontgomeryCountyAirParkTaskRS

    def __init__(self):
        super().__init__()

        # Enters the data and prepares the state for data processing

    def tearup(self, initial_url: str, downloads_path: str, rds: Optional[Redis] = None,
               attempts: Optional[int] = 3, print_ip_addresses: bool = True, max_attempts: int = 10,
               recaptcha_score_threshold: int = 7, proxy_variation: Optional[str] = None) -> list[str]:
        for retry in range(attempts):
            self.log(f'Retrying to get to Maryland page during tearup: {retry + 1} out of {attempts}')
            changed = self.change_proxy_repeat(print_ip_addresses, max_attempts,
                                               recaptcha_score_threshold, proxy_variation)
            if changed != '':
                self.log(changed)
                continue
            else:
                self.log('Proxy successfully changed during tearup')

            # Disable loading of blocked URLS like recaptcha or google tag
            blocked_urls = self.get_prepare_block_urls()
            if len(blocked_urls) > 0:
                self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": blocked_urls})
                self.driver.execute_cdp_cmd('Network.enable', {})
            self.RS = self.prepare(initial_url, downloads_path)
            if len(blocked_urls) > 0:
                self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": []})
                self.driver.execute_cdp_cmd('Network.enable', {})

            return self.RS.Logs

        raise Exception(f'Failed to obtain Maryland page during tearup after {attempts} attempts')

    def teardown(self, initial_url: str, downloads_path: str = None, rds: Redis | None = None,
                 attempts: Optional[int] = 3, print_ip_addresses: bool = True, max_attempts: int = 10,
                 recaptcha_score_threshold: int = 7, proxy_variation: Optional[str] = None) -> list[str]:
        for retry in range(attempts):
            self.log(f'Retrying to get to Maryland page during teardown: {retry + 1} out of {attempts}')
            changed = self.change_proxy_repeat(print_ip_addresses, max_attempts, recaptcha_score_threshold,
                                               proxy_variation)
            if changed != '':
                self.log(changed)
                continue
            else:
                self.log('Proxy successfully changed during teardown')
                self.RS = self.prepare(initial_url, downloads_path)

            # Disable loading of blocked URLS like recaptcha or google tag
            blocked_urls = self.get_prepare_block_urls()
            if len(blocked_urls) > 0:
                self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": blocked_urls})
                self.driver.execute_cdp_cmd('Network.enable', {})
            self.RS = self.prepare(initial_url, downloads_path)
            if len(blocked_urls) > 0:
                self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": []})
                self.driver.execute_cdp_cmd('Network.enable', {})

            return self.RS.Logs

        raise Exception(f'Failed to obtain Maryland page during teardown after {attempts} attempts')

    def prepare(self, initial_url: str, downloads_path: str) -> MontgomeryCountyAirParkTaskRS:
        try:
            self.log('Obtaining initial page URL')
            self.SB.get(initial_url)
        except WebDriverException as wex:
            self.error('Error obtaining the initial page URL: ' + str(wex))
            self.RS.Body = self.driver.page_source
            return self.RS

        self.log('Initial page URL obtained')
        self.RS.Stage = STAGE_OBTAINED_PAGE

        try:
            self.wait_for_page_to_load(20000)
        except BaseException as e:
            self.error('Failed to load the page: ' + str(e))
            self.RS.Body = self.driver.page_source
            return self.RS

        wait_five = WebDriverWait(self.driver, 5, poll_frequency=0.5)
        try:
            wait_five.until(EC.visibility_of_element_located((By.ID, 'First Name')))
        except BaseException as ex:
            self.log('Failed to find first name field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        return self.RS

    def process(self, initial_url: str, downloads_path: str) -> MontgomeryCountyAirParkTaskRS:
        start_date = get_date(self.RQ.StartDate)
        if start_date is None:
            self.error(f'Failed to interpret start date {self.RQ.StartDate}')
            return self.RS

        end_date = get_date(self.RQ.EndDate)
        if end_date is None:
            self.error(f'Failed to interpret end date {self.RQ.EndDate}')
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'First Name')):
                self.log('First name field is visible at ' + self.driver.current_url)
                first_name_element = self.SB.find_element(By.ID, 'First Name')
            else:
                raise Exception('First name field is not visible')
        except BaseException as ex:
            self.log('Failed to find first name field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering first name into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", first_name_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(first_name_element)
            actions.click()
            self.human_like_typing(first_name_element, self.RQ.FirstName)
        except BaseException as ex:
            self.log('Failed to enter first name into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'Last Name')):
                self.log('Last name field is visible at ' + self.driver.current_url)
                last_name_element = self.SB.find_element(By.ID, 'Last Name')
            else:
                raise Exception('Last name field is not visible')
        except BaseException as ex:
            self.log('Failed to find last name field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering last name into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", last_name_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(last_name_element)
            actions.click()
            self.human_like_typing(last_name_element, self.RQ.LastName)
        except BaseException as ex:
            self.log('Failed to enter last name into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'email')):
                self.log('E-mail address field is visible at ' + self.driver.current_url)
                email_address_element = self.SB.find_element(By.ID, 'email')
            else:
                raise Exception('E-mail address field is not visible')
        except BaseException as ex:
            self.log('Failed to find e-mail address field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering e-mail address into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", email_address_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(email_address_element)
            actions.click()
            self.human_like_typing(email_address_element, self.RQ.EmailAddress)
        except BaseException as ex:
            self.log('Failed to enter e-mail address into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'Phone Number')):
                self.log('Phone number field is visible at ' + self.driver.current_url)
                phone_number_element = self.SB.find_element(By.ID, 'Phone Number')
            else:
                raise Exception('Phone number field is not visible')
        except BaseException as ex:
            self.log('Failed to find phone number field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering phone number into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", phone_number_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(phone_number_element)
            actions.click()
            self.human_like_typing(phone_number_element, self.RQ.PhoneNumber)
        except BaseException as ex:
            self.log('Failed to enter phone number into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'Street Address Cross Streets')):
                self.log('Street address field is visible at ' + self.driver.current_url)
                street_address_element = self.SB.find_element(By.ID, 'Street Address Cross Streets')
            else:
                raise Exception('Street address field is not visible')
        except BaseException as ex:
            self.log('Failed to find street address field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering street address into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", street_address_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(street_address_element)
            actions.click()
            self.human_like_typing(street_address_element, self.RQ.StreetAddress)
        except BaseException as ex:
            self.log('Failed to enter street address into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'City')):
                self.log('City address field is visible at ' + self.driver.current_url)
                city_address_element = self.SB.find_element(By.ID, 'City')
            else:
                raise Exception('City address field is not visible')
        except BaseException as ex:
            self.log('Failed to find city address field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering city address into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", city_address_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(city_address_element)
            actions.click()
            self.human_like_typing(city_address_element, self.RQ.CityAddress)
        except BaseException as ex:
            self.log('Failed to enter city address into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'State')):
                self.log('State address field is visible at ' + self.driver.current_url)
                state_address_element = self.SB.find_element(By.ID, 'State')
            else:
                raise Exception('State address field is not visible')
        except BaseException as ex:
            self.log('Failed to find state address field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering state address into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", state_address_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(state_address_element)
            actions.click()
            self.human_like_typing(state_address_element, self.RQ.StateAddress)
        except BaseException as ex:
            self.log('Failed to enter state address into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'ZIP')):
                self.log('ZIP address field is visible at ' + self.driver.current_url)
                zip_address_element = self.SB.find_element(By.ID, 'ZIP')
            else:
                raise Exception('ZIP address field is not visible')
        except BaseException as ex:
            self.log('Failed to find ZIP address field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering ZIP address into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", zip_address_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(zip_address_element)
            actions.click()
            self.human_like_typing(zip_address_element, self.RQ.ZIPAddress)
        except BaseException as ex:
            self.log('Failed to enter ZIP address into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            script = ("(function(){"
                      f"document.getElementsByName('form[Approximate Start Date Time]')[0].value = '{start_date.strftime('%d-%m-%Y') + ' ' + self.RQ.StartTime}';"
                      f"document.getElementsByName('hidden[3_Approximate Start Date Time]')[0].value = '{start_date.strftime('%m/%d/%Y') + ' ' + self.RQ.StartTime}';"
                      f"document.getElementsByName('form[Approximate End Date Time]')[0].value = '{end_date.strftime('%d-%m-%Y') + ' ' + self.RQ.EndTime}';"
                      f"document.getElementsByName('hidden[3_Approximate End Date Time]')[0].value = '{end_date.strftime('%m/%d/%Y') + ' ' + self.RQ.EndTime}';"
                      "})()")

            self.driver.execute_script(script)
        except BaseException as ex:
            self.log('Failed to find start date & time field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        if self.RQ.AirportSourceNameCode:
            try:
                if EC.visibility_of_element_located((By.ID, 'Airport source name code')):
                    self.log('Airport source name code field is visible at ' + self.driver.current_url)
                    airport_name_code_element = self.SB.find_element(By.ID, 'Airport source name code')
                else:
                    raise Exception('Airport source name code field is not visible')
            except BaseException as ex:
                self.log('Failed to find airport source name code field and/or scroll it into view: ' + str(ex))
                self.RS.Body = self.driver.page_source
                return self.RS

            try:
                self.log('Entering Airport source name code into the field')
                self.driver.execute_script("arguments[0].scrollIntoView(true);", airport_name_code_element)
                actions = ActionChains(self.driver)
                actions.move_to_element(airport_name_code_element)
                actions.click()
                self.human_like_typing(airport_name_code_element, self.RQ.AirportSourceNameCode)
            except BaseException as ex:
                self.log('Failed to enter airport source name code into field: ' + str(ex))
                self.RS.Body = self.driver.page_source
                return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'Aircraft Type')):
                self.log('Description/question field is visible at ' + self.driver.current_url)
                aircraft_type_element = self.SB.find_element(By.ID, 'Aircraft Type')
            else:
                raise Exception('Aircraft type field is not visible')
        except BaseException as ex:
            self.log('Failed to find aircraft type field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering aircraft type into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", aircraft_type_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(aircraft_type_element)
            actions.click()
            self.human_like_typing(aircraft_type_element, self.RQ.AircraftType)
        except BaseException as ex:
            self.log('Failed to enter aircraft type into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'Description Question')):
                self.log('Description/question field is visible at ' + self.driver.current_url)
                description_question_element = self.SB.find_element(By.ID, 'Description Question')
            else:
                raise Exception('Description/question field is not visible')
        except BaseException as ex:
            self.log('Failed to find description/question field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering description/question into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", description_question_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(description_question_element)
            actions.click()
            self.human_like_typing(description_question_element, self.RQ.DescriptionOrQuestion)
        except BaseException as ex:
            self.log('Failed to enter description/question into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            if EC.visibility_of_element_located((By.ID, 'Response requested')):
                self.log('Response request field is visible at ' + self.driver.current_url)
                response_request_element = self.SB.find_element(By.ID, 'Response requested')
            else:
                raise Exception('Response request field is not visible')
        except BaseException as ex:
            self.log('Failed to find response request field and/or scroll it into view: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        try:
            self.log('Entering response request into the field')
            self.driver.execute_script("arguments[0].scrollIntoView(true);", response_request_element)
            actions = ActionChains(self.driver)
            actions.move_to_element(response_request_element)
            actions.click()
            self.human_like_typing(response_request_element, self.RQ.ResponseRequested)
        except BaseException as ex:
            self.log('Failed to enter response request into field: ' + str(ex))
            self.RS.Body = self.driver.page_source
            return self.RS

        for retries in range(3):
            if initial_url == self.driver.current_url:
                try:
                    self.log('Clicking on the `Send` button')
                    element = self.SB.find_element(By.ID, 'Send')
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(5)
                    self.wait_for_page_to_load(10000)
                except BaseException as ex:
                    self.log('Failed to click on the `Send` button on the page: ' + str(ex))
                    self.RS.Body = self.driver.page_source
                    return self.RS
            else:
                break

        if 'Please complete all required fields!' in self.driver.page_source:
            raise RetryException('Failed to submit the form with provided data')

        # Callback here
        self.RS.Body = "All done successfully"
        return self.RS
