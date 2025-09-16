from selenium_worker.Requests.MontgomeryCountyAirParkTaskRQ import MontgomeryCountyAirParkTaskRQ, \
    MontgomeryCountyAirParkTaskRQEncoder
from selenium_worker.Responses.MontgomeryCountyAirParkTaskRS import MontgomeryCountyAirParkTaskRS, \
    MontgomeryCountyAirParkTaskRSEncoder
from selenium_worker.Services.MontgomeryCountyAirParkTask import MontgomeryCountyAirParkTask
from selenium_worker.enums import WorkerType

task_names = {
    WorkerType.Montgomery: 'montgomery'
}

task_queues = {
    WorkerType.Montgomery: 'montgomery-queue'
}

task_page_urls = {
    WorkerType.Montgomery: 'https://www.montgomerycountyairpark.com/noisecomplaint'
}

task_type_classes = {
    WorkerType.Montgomery: [
        MontgomeryCountyAirParkTask, 
        MontgomeryCountyAirParkTaskRQ,
        MontgomeryCountyAirParkTaskRQEncoder, 
        MontgomeryCountyAirParkTaskRS,
        MontgomeryCountyAirParkTaskRSEncoder
    ]
}

task_type_names = {
    WorkerType.Montgomery: "Montgomery County Airpark"
}

minimum_recaptcha_scores = {
    WorkerType.Montgomery: 3
}
