import json
import logging
import os
import platform
import signal
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from typing import Optional
from celery.exceptions import MaxRetriesExceededError

# Disable SeleniumBase colored tracebacks to prevent terminal issues during shutdown
os.environ['DISABLE_COLORED_TRACEBACK'] = '1'

import celery
from celery import signals
from celery.concurrency import asynpool
from dotenv import load_dotenv
from pyvirtualdisplay import Display
from pyvirtualdisplay.abstractdisplay import XStartTimeoutError
from requests.exceptions import ProxyError
from selenium.common import TimeoutException, WebDriverException

import selenium_worker.config as cfg
from selenium_worker.Requests.WorkTaskRQ import WorkTaskRQ, WorkTaskRQEncoder
from selenium_worker.Responses.WorkTaskRS import WorkTaskRS, WorkTaskRSEncoder
from selenium_worker.Services.TaskService import TaskService
from selenium_worker.exceptions import RetryException
from selenium_worker.vars import task_type_classes, task_page_urls, task_type_names, \
    worker_type_minimum_recaptcha_scores, task_queues, task_names
from selenium_worker.enums import WorkerType
from selenium_worker.utils import date_parser, date_encoder, build_pypasser_config_json, build_nopecha_config, \
    time_diff_ms

logger = logging.getLogger(__name__)

task_service: Optional[TaskService] = None
display: Optional[Display] = None
worker_started_at: Optional[datetime] = None
last_task_finished_at: Optional[datetime] = None

logger.info('Creating Celery application ...')
app = celery.Celery(
    'selenium_tasks',
    broker="redis://{}:{}".format(cfg.RedisSettings.REDIS_HOST, cfg.RedisSettings.REDIS_PORT),
    backend="redis://{}:{}".format(cfg.RedisSettings.REDIS_HOST, cfg.RedisSettings.REDIS_PORT)
)
logger.info('Celery application was created successfully')

@signals.worker_process_init.connect
def init(**args):
    global display
    global task_service
    logger.info('Begin worker initialization ...')

    worker_started_at = datetime.now(timezone.utc)
    try:
        if cfg.GeneralSettings.WORKER_TYPE == -1:
            raise Exception('Missing worker type value')
        if 'windows' in platform.system().lower() and display is None:
            try:
                display = Display(visible=False, size=(1920, 1080))
                display.start()
            except XStartTimeoutError as xe:
                logger.error(
                    'Virtual display error during worker initialization: {}: {}'.format(xe, traceback.format_exc()))
                if task_service is not None and task_service.driver is not None:
                    task_service.shutdown()
                logger.error(
                    f'Terminating {cfg.GeneralSettings.WORKER_TYPE} worker process with UID of {os.getpid()} due to display error')
                os.kill(os.getpid(), signal.SIGKILL)
                return None

        logger.info('Starting worker initialization ...')
        initial_url = task_page_urls[cfg.GeneralSettings.worker_type()]
        task_type = task_names[cfg.GeneralSettings.worker_type()]
        service_type, request_type, request_encoder_type, response_type, response_encoder_type = task_type_classes[
                                                                                 cfg.GeneralSettings.worker_type()][:]
        if request_type is None:
            logger.error(f'Invalid worker type: ${cfg.GeneralSettings.WORKER_TYPE}')
            return None

        request = request_type({})
        if task_service is None:
            task_service = service_type()
        if task_service is None:
            logger.error(f'Cannot instantiate service class for worker type of {cfg.GeneralSettings.WORKER_TYPE}')
            return None

        response = response_type()
        response.Logs = list()
        response.Error = ''
        task_service.RS = response
        response_encoder = response_encoder_type()

        minimum_recaptcha_score = cfg.ProxySettings.MIN_RECAPTCHA_SCORE
        if cfg.GeneralSettings.worker_type() in worker_type_minimum_recaptcha_scores.keys():
            minimum_recaptcha_score = worker_type_minimum_recaptcha_scores[cfg.GeneralSettings.worker_type()]

        task_service.init_browser(cfg.GeneralSettings.browser_driver_type(), task_type)
        task_service.driver.set_page_load_timeout(20.0)
        task_service.driver.switch_to.window(task_service.driver.current_window_handle)

        logger.info(f'=== {task_type_names[cfg.GeneralSettings.worker_type()]} TEAR-UP BEGIN ===')
        task_service.tearup(initial_url=initial_url, downloads_path=cfg.CacheSettings.DOWNLOADS_PATH,
                            rds=rds, recaptcha_score_threshold=minimum_recaptcha_score)
        logger.info(f'=== {task_type_names[cfg.GeneralSettings.worker_type()]} TEAR-UP COMPLETE ===')
        return None

    except ProxyError as pe:
        logger.error('Proxy exception during worker initialization: {}: {}'.format(pe, traceback.format_exc()))
        if task_service is not None and task_service.driver is not None:
            task_service.shutdown()
        logger.error(
            f'Terminating {cfg.GeneralSettings.WORKER_TYPE} worker process with UID of {os.getpid()} due to proxy error')
        os.kill(os.getpid(), signal.SIGKILL)
        return None
    except Exception as e:
        logger.error('General exception during worker initialization: {}: {}'.format(e, traceback.format_exc()))
        if task_service is not None and task_service.driver is not None:
            task_service.shutdown()
        logger.error(f'Terminating worker process with UID of {os.getpid()} due to Exception')
        os.kill(os.getpid(), signal.SIGKILL)
        return None


@signals.worker_process_shutdown.connect
def deinit(**args):
    global display
    global task_service

    try:
        logger.info('De-initializing worker process with ID {}'.format(os.getpid()))
        if not (display is None):
            display.stop()
        task_service.shutdown()
    except Exception as e:
        logger.error('General exception during worker de-initialization: {} - {}'.format(e, traceback.format_exc()))
        logger.error(f'Terminating process with ID of {os.getpid()} due to Exception in deinit')
        os.kill(os.getpid(), signal.SIGKILL)


@signals.task_postrun.connect
def should_restart(**args):
    global display
    global task_service
    global last_task_finished_at

    meta = rds.get('job.{}'.format(args['task_id'])) or '{}'
    meta = json.loads(meta, object_hook=date_parser)

    last_task_finished_at = datetime.now(timezone.utc)

    # If no value specified, exit and do not do postrun
    if 'task_post_run' not in meta or meta['task_post_run'] is None or meta['task_post_run'] == '':
        return None

    try:
        for retry in range(3):
            try:
                if cfg.GeneralSettings.WORKER_TYPE != -1 and cfg.GeneralSettings.worker_type() in task_page_urls.keys():
                    service_type, request_type, request_encoder_type, response_type, response_encoder_type = task_type_classes[cfg.GeneralSettings.worker_type()][:]
                    initial_url = task_page_urls[cfg.GeneralSettings.worker_type()]
                    request = request_type({})
                    request.Type = cfg.GeneralSettings.WORKER_TYPE
                    if task_service is None:
                        task_service = service_type(RQ=request)

                    logger.info(f'Performing tear-down - {retry + 1} out of 3...')
                    # Shutdown browser so that it is re-created to continue from cached state
                    task_service.shutdown(True)
                    
                    minimum_recaptcha_score = 3
                    if cfg.GeneralSettings.worker_type() not in worker_type_minimum_recaptcha_scores:
                        logger.warning(
                            f'Missing minimum reCAPTCHA score for state with WorkerType of {cfg.GeneralSettings.WORKER_TYPE}, using default of 1')
                    else:
                        minimum_recaptcha_score = worker_type_minimum_recaptcha_scores[cfg.GeneralSettings.worker_type()]
                    
                    # Prepare driver and user data directory
                    task_service.init_browser(cfg.GeneralSettings.browser_driver_type(),
                                              cfg.GeneralSettings.worker_type())
                    task_service.driver.switch_to.window(task_service.driver.current_window_handle)
                    logger.info(f'=== {task_type_names[cfg.GeneralSettings.worker_type()]} TEAR-DOWN BEGIN ===')

                    task_service.teardown(initial_url=initial_url, downloads_path=cfg.CacheSettings.DOWNLOADS_PATH,
                                          rds=rds, recaptcha_score_threshold=minimum_recaptcha_score)

                    response = WorkTaskRS()
                    response.Logs = list()
                    response.Error = ''
                    task_service.RS = response

                    logger.info(f'=== {task_type_names[cfg.GeneralSettings.worker_type()]} TEAR-DOWN COMPLETE ===')
                    return None
                return None
            except Exception as e:
                task_service.shutdown()
                logger.error(f'Terminating process with ID of {os.getpid()} due to Exception in should_restart')
                os.kill(os.getpid(), signal.SIGKILL)
                return None
    except:
        pass

    return None


@app.task(name='task_worker.work', bind=True, TASK_REJECT_ON_WORKER_LOST=cfg.task_reject_on_worker_lost)
def work(self, request, job_uid: str):
    global display
    global task_service

    meta = None

    request_encoder = WorkTaskRQEncoder()
    rq = WorkTaskRQ(request)
    response = WorkTaskRS()
    response.Logs = list()
    response.Error = ''
    response_encoder = WorkTaskRSEncoder()

    try:
        if task_service is None:
            logger.error(f'Service class for state with worker type of {cfg.GeneralSettings.WORKER_TYPE} does not exist')
            return None

        logger.info('Begin processing of job with UID {}'.format(job_uid))
        if cfg.GeneralSettings.WORKER_TYPE == -1:
            raise Exception('Missing worker type value')

        meta = rds.get('job.{}'.format(job_uid)) or '{}'
        meta = json.loads(meta, object_hook=date_parser)
        meta['started_at'] = datetime.now(timezone.utc)
        meta['task_post_run'] = job_uid  # This is to indicate that task' post-run signal needs to execute
        rds.set('job.{}'.format(job_uid), json.dumps(meta, default=date_encoder))

        if rq.Type is None:
            response.Error = 'Missing worker type parameter'
            if meta is not None:
                rds.set('job.{}'.format(job_uid), json.dumps(meta, default=date_encoder))
            return response_encoder.encode(response)

        if rq.Type != cfg.GeneralSettings.WORKER_TYPE:
            raise Exception('Worker is processing worker type of {}, not {}', cfg.GeneralSettings.WORKER_TYPE,
                            rq.Type)
        service_type, request_type, request_encoder_type, response_type, response_encoder_type = \
            task_type_classes[WorkerType(rq.Type)][:]
        initial_url = task_page_urls[WorkerType(rq.Type)]

        request: WorkTaskRQ = request_type(request)
        request_encoder = request_encoder_type()

        response = response_type()
        response_encoder = response_encoder_type()

        request.SessionUID = job_uid
        task_service.RQ = request
        task_service.RS = response

        validation_errors = request.validate()
        if validation_errors:
            logger.error('Errors in the request: {}'.format(validation_errors))
            response.Errors = validation_errors
            if meta is not None:
                rds.set('job.{}'.format(job_uid), json.dumps(meta, default=date_encoder))
            return response_encoder.encode(response)

        logger.info(f'Processing worker type task for {rq.Type} and data {request_encoder.encode(request)} ...')

        with tempfile.TemporaryDirectory() as temp_dir:
            # task_service.driver.execute_script("window.stop();")
            time.sleep(1.5 / 10)
            time_started = datetime.now()
            task_service.RQ = request

            # Disable loading of blocked URLS like recaptcha or google tag
            blocked_urls = task_service.get_process_block_urls()
            if len(blocked_urls) > 0:
                task_service.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": blocked_urls})
                task_service.driver.execute_cdp_cmd('Network.enable', {})
            
            # Process the request using the task service
            response = task_service.process(initial_url, temp_dir)
            
            # Re-enable loading of blocked URLS like recaptcha or google tag
            if len(blocked_urls) > 0:
                task_service.driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": []})
                task_service.driver.execute_cdp_cmd('Network.enable', {})
                
            processing_total = time_diff_ms(datetime.now(), time_started)
            logger.info(f'Total processing execution time for job {job_uid} is ' + str(
                processing_total) + ' ms.')
            meta['processing_total'] = processing_total
        
        # Job complete, encode the result
        if meta is not None:
            rds.set('job.{}'.format(job_uid), json.dumps(meta, default=date_encoder))

        return response_encoder.encode(response)

    except TimeoutException as e:
        logger.error(f"TimeoutException caught for job {job_uid}: {e} - {traceback.format_exc()}")
        task_service.shutdown()
        logger.error(f'Terminating process with ID of {os.getpid()} due to Timeout exception')
        os.kill(os.getpid(), signal.SIGKILL)
        return None
    except NameError as e:
        logger.error("Name error, please try again: {} - {}".format(e, traceback.format_exc()))
        task_service.shutdown()
        logger.error(f'Terminating process with ID of {os.getpid()} due to NameError exception')
        os.kill(os.getpid(), signal.SIGKILL)
        return None
    except WebDriverException as e:
        logger.error("Error with webdriver, please try again: {} - {}".format(e, traceback.format_exc()))
        task_service.shutdown()
        logger.error(f'Terminating process with ID of {os.getpid()} due to WebDriver exception')
        os.kill(os.getpid(), signal.SIGKILL)
        return None
    except RetryException as re:
        logger.warning('Failed to obtain results, retrying')
        raise self.retry(countdown=request.Countdown, max_retries=request.MaxRetries)
    except MaxRetriesExceededError as mree:
        logger.error("Failed to obtain results after exhausting all retries: {} - {}".format(mree, traceback.format_exc()))
        task_service.shutdown()
        logger.error(f'Terminating process with ID of {os.getpid()} due to maximum retries reached exception')
        os.kill(os.getpid(), signal.SIGKILL)
        return None
    except Exception as e:
        logger.error("General exception, please try again: {} - {}".format(e, traceback.format_exc()))
        task_service.shutdown()
        logger.error(f'Terminating process with ID of {os.getpid()} due to Exception')
        os.kill(os.getpid(), signal.SIGKILL)
        return None
    except BaseException as be:
        logger.critical("Unexpected base exception: {} - {}".format(be, traceback.format_exc()))
        task_service.shutdown()
        logger.critical(f'Terminating process with ID of {os.getpid()} due to BaseException')
        os.kill(os.getpid(), signal.SIGKILL)
        return None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f'Received signal {signum}, shutting down...')
    sys.exit(0)

if __name__ == '__main__' or __name__ == 'main':
    load_dotenv()

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info('Connecting to Redis ...')
    rds = cfg.RedisSettings.rds()

    logger.info('Updating PyPasser extension configuration ...')
    build_pypasser_config_json()

    logger.info('Updating nopeCHA configuration ...')
    build_nopecha_config()

    logger.info('Registering tasks ...')
    asynpool.PROC_ALIVE_TIMEOUT = 240
    app.tasks.register(work)
    app.config_from_object(cfg)

    logger.info('Checking for existence of paths ...')
    if not os.path.exists(cfg.CacheSettings.DATA_PATH):
        os.mkdir(cfg.CacheSettings.DATA_PATH)
    if not os.path.exists(cfg.CacheSettings.DISK_PATH):
        os.mkdir(cfg.CacheSettings.DISK_PATH)
    if not os.path.exists(cfg.CacheSettings.BROWSER_PATH):
        os.mkdir(cfg.CacheSettings.BROWSER_PATH)
    if not os.path.exists(cfg.CacheSettings.GLOBALCACHE_PATH):
        raise Exception(f'Missing mount for {cfg.CacheSettings.GLOBALCACHE_PATH}')

    worker_queue = task_queues[cfg.GeneralSettings.worker_type()]
    argv = ['worker', '--concurrency=1', f'--queues={worker_queue}', '--pool=solo', '--loglevel=INFO', '-Ofair']
    logger.info('Starting worker of type {} and UID of {} on queue {}...'.format(cfg.GeneralSettings.WORKER_TYPE,
                                                                           cfg.GeneralSettings.WORKER_UID,
                                                                           worker_queue))

    # Verify Celery app configuration
    logger.debug(f'Celery app broker: {app.conf.broker_url}')
    logger.debug(f'Celery app backend: {app.conf.result_backend}')
    logger.debug(f'Registered tasks: {list(app.tasks.keys())}')
    try:
        logger.debug(f'Creating Celery worker with args: {argv}')
        worker = app.worker_main(argv)
        if worker is not None:
            logger.info('Celery worker created successfully, starting...')
            worker.start()
        else:
            logger.error('Failed to create Celery worker - worker_main returned None')
    except KeyboardInterrupt:
        logger.info('Received keyboard interrupt during worker startup, shutting down gracefully...')
        sys.exit(0)
    except SystemExit:
        logger.info('Received system exit signal, shutting down gracefully...')
        sys.exit(0)
    except Exception as e:
        logger.error(f'Error starting worker: {e}', exc_info=True)
        sys.exit(1)
