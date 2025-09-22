import logging
import time
from typing import Optional

from redis import Redis
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from selenium_worker.Requests.MontgomeryCountyAirParkTaskRQ import MontgomeryCountyAirParkTaskRQ
from selenium_worker.Responses.MontgomeryCountyAirParkTaskRS import MontgomeryCountyAirParkTaskRS
from selenium_worker.Services.TaskService import TaskService, PageSetupConfig
from selenium_worker.constants import STAGE_OBTAINED_PAGE
from selenium_worker.exceptions import RetryException

logger = logging.getLogger(__name__)


class MontgomeryCountyAirParkTask(TaskService):
    RQ: MontgomeryCountyAirParkTaskRQ
    RS: MontgomeryCountyAirParkTaskRS

    def __init__(self):
        super().__init__()

        # Enters the data and prepares the state for data processing

    def _execute_page_setup(self, method_name: str, config: PageSetupConfig) -> list[str]:
        """
        Common implementation for tearup and teardown methods.

        Args:
            method_name: The name of the calling method for logging purposes
            config: Configuration object containing all setup parameters

        Returns:
            List of log messages from the response

        Raises:
            Exception: If unable to obtain Maryland page after all attempts
        """
        for retry in range(config.attempts):
            self.log(f'Retrying to get to Maryland page during {method_name}: {retry + 1} out of {config.attempts}')
            changed = self.change_proxy_repeat(config.print_ip_addresses, config.max_attempts,
                                               config.recaptcha_score_threshold, config.proxy_variation)
            if changed != '':
                self.log(changed)
                continue
            else:
                self.log(f'Proxy successfully changed during {method_name}')

            # Disable loading of blocked URLS like recaptcha or google tag
            blocked_urls = self.get_prepare_block_urls()
            if len(blocked_urls) > 0:
                self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": blocked_urls})
                self.driver.execute_cdp_cmd('Network.enable', {})

            # Prepare the page for submission
            self.RS = self.prepare(config.initial_url, config.downloads_path)

            # Re-enable loading of blocked URLS like recaptcha or google tag
            if len(blocked_urls) > 0:
                self.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": []})
                self.driver.execute_cdp_cmd('Network.enable', {})

            return self.RS.Logs

        raise Exception(f'Failed to obtain Maryland page during {method_name} after {config.attempts} attempts')

    def tearup(self, config: PageSetupConfig) -> list[str]:
        """
        Prepare the state page before submitting form data with ID/DL data.

        Args:
            config: Configuration object containing all setup parameters

        Returns:
            List of log messages from the response
        """
        return self._execute_page_setup("tearup", config)

    def teardown(self, config: PageSetupConfig) -> list[str]:
        """
        Prepare the state page after ID/DL data was obtained.

        Args:
            config: Configuration object containing all setup parameters

        Returns:
            List of log messages from the response
        """
        return self._execute_page_setup("teardown", config)

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
        # Comment out for testing
        
        # try:
        #     # Fill all the basic form fields
        #     self.fill_form_field(By.ID, 'First Name', 'first name', self.RQ.FirstName)
        #     self.fill_form_field(By.ID, 'Last Name', 'last name', self.RQ.LastName)
        #     self.fill_form_field(By.ID, 'email', 'e-mail address', self.RQ.EmailAddress)
        #     self.fill_form_field(By.ID, 'Phone Number', 'phone number', self.RQ.PhoneNumber)
        #     self.fill_form_field(By.ID, 'Street Address Cross Streets', 'street address', self.RQ.StreetAddress)
        #     self.fill_form_field(By.ID, 'City', 'city address', self.RQ.CityAddress)
        #     self.fill_form_field(By.ID, 'State', 'state address', self.RQ.StateAddress)
        #     self.fill_form_field(By.ID, 'ZIP', 'ZIP address', self.RQ.ZIPAddress)

        #     # Fill date/time fields using JavaScript with computed properties
        #     script = ("(function(){"
        #               f"document.getElementsByName('form[Approximate Start Date Time]')[0].value = '{self.RQ.startDateTime}';"
        #               f"document.getElementsByName('hidden[3_Approximate Start Date Time]')[0].value = '{self.RQ.hiddenStartDateTime}';"
        #               f"document.getElementsByName('form[Approximate End Date Time]')[0].value = '{self.RQ.startDateTime}';"
        #               f"document.getElementsByName('hidden[3_Approximate End Date Time]')[0].value = '{self.RQ.hiddenStartDateTime}';"
        #               "})()")
        #     self.driver.execute_script(script)
            
        #     # Fill the remaining fields
        #     self.fill_form_field(By.ID, 'Airport source name code', 'airport source name code', self.RQ.AirportSourceNameCode)
        #     self.fill_form_field(By.ID, 'Aircraft Type', 'aircraft type', self.RQ.AircraftType)
        #     self.fill_form_field(By.ID, 'Description Question', 'description/question', self.RQ.DescriptionOrQuestion + ' (' + self.RQ.SessionUID + ')')
        #     self.fill_form_field(By.ID, 'Response requested', 'response request', self.RQ.ResponseRequested)

        # except BaseException as ex:
        #     return self.RS

        # for retries in range(3):
        #     if initial_url == self.driver.current_url:
        #         try:
        #             self.log('Clicking on the `Send` button')
        #             element = self.SB.find_element(By.ID, 'Send')
        #             self.driver.execute_script("arguments[0].click();", element)
        #             time.sleep(5)
        #             self.wait_for_page_to_load(10000)
        #         except BaseException as ex:
        #             self.log('Failed to click on the `Send` button on the page: ' + str(ex))
        #             self.RS.Body = self.driver.page_source
        #             return self.RS
        #     else:
        #         break

        # if 'Please complete all required fields!' in self.driver.page_source:
        #     raise RetryException('Failed to submit the form with provided data')

        # Callback here
        self.RS.Body = "All done successfully"
        return self.RS
