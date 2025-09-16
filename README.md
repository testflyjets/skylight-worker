# Requirements

Redis
Python 3.12+
Pip 25+

OxyLabs account with residential/mobile proxies traffic available

# Installation

- Run refresh.sh to install all requirements from requirements.txt
- Create a directory where Chrome will be storing its data - by default, it is /var/tmp/cache. Change if needed in .env
  file - child directories will be created automatically at start-up.
- Set Redis credentials if needed in .env file
- Add OxyLabs username/password into .env `PROXY_USERNAME/PROXY_PASSWORD`

# Running

Worker can be started by running `python3 -m selenium_worker.app` - it should start Chrome browser and open it on about:
blank page.
Browser will have chrome proxy plugin added to its extensions list.

# Sending tasks to worker

Task can be sent to API that will pass it to Celery - see API documentation for it.
Worker tasks can be found in `selenium_worker/app.py` file - they're annotated with `@app.task`.
Worker has initialization logic in `init` (when you start the worker), and de-initialization logic in `deinit` (when
worker shuts down), and `should_restart` for post-task things needed to be done.

# Proxy

Proxy has three modes:

- DISABLED - Not proxying any requests
- INCLUSIVE - Proxying only selected URLS
- EXCLUSIVE - Proxying everything except selected URLS

Selected URLs are specified in `DEFAULT_PROXY_DOMAINS` variable. Whenever you need to change proxy, call
`change_proxy_repeat` for making use of reCAPTCHA score checking until a proxy with high enough score is found.
Otherwise `change_proxy` can be used to obtain a different proxy. Proxies differentiate by using a different port on
us-pr.oxylabs.io domain, as well as having a different username.

# Examples

Replace `___random_uuid_string_here___` with a random UUID string - this is unique job identifier by which you can
obtain its state.

Perform work request: `curl --location 'http://localhost:8080/jobs/work/___random_uuid_string_here___' \
--header 'Content-Type: application/json' \
--data '
{
    "Queue" : "task01",
    "FirstName" : "",
    "LastName" : "",
    "Debug": false
}
'`

Perform cache request: `curl --location 'http://localhost:8080/jobs/cache/___random_uuid_string_here___' \
--header 'Content-Type: application/json' \
--data '
{
    "Queue" : "task01",
    "FirstName" : "",
    "LastName" : "",
    "Debug": false
}
'`

# How it works

- Create Chrome browser instance with required parameters (incognito etc)
- Load proxy extension that will be responsible for changing Chrome proxy
- Wait for incoming task requests through Celery

When `change_proxy_fake` is called, it will be picked up by extension and a call to `change_proxy` will be made to
obtain PAC (proxy auto-configuration) script. Username will also be generated and stored alongside PAC script in
extension for Chrome to use when visiting websites.

# Notes

- Locally obtaining a proxied IP address requires making a request to `PROXIED_IP_SERVICE_URL`. When worker is
  deployed (with API) to the cloud, this variable can be removed and worker will be making requests to API_URL/my_ip to
  avoid any issues with limits of 3rd party API.
- Keep in mind that when cache of browser profile is created, the proxy extension is not overwritten when its code is
  changed. You need to re-cache in order for new browser profile created anew - that will create blank profile with
  updated extension.