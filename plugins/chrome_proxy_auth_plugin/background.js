let proxyCredentials = {};

// When PAC script determines that URL goes through proxy, it asks for authentication
chrome.webRequest.onAuthRequired.addListener(function (details) {
    return {authCredentials: proxyCredentials}
}, {urls: ["<all_urls>"]}, ['blocking']);

// Here we receive change proxy request (to a fake address)
// We make explicit fetch request to actual proxy PAC script location
// And assign it to chrome proxy settings
chrome.webRequest.onBeforeRequest.addListener(function (details) {
    if (details.method === "GET" && details.type === "main_frame") {
        // Obtain data from URL query parameters
        const url = new URL(details.url);
        // Do not process any other URLs to API besides get_proxy_details_fake
        if (!url.pathname.indexOf('get_proxy_details_fake'))
            return;

        if (!url.searchParams.has('proxy_host') || url.searchParams.get('proxy_host') === '') return;
        let PROXY_HOST = url.searchParams.get('proxy_host');
        if (!url.searchParams.has('proxy_protocol') || url.searchParams.get('proxy_protocol') === '') return;
        let PROXY_PROTOCOL = url.searchParams.get('proxy_protocol');
        if (!url.searchParams.has('proxy_username') || url.searchParams.get('proxy_username') === '') return;
        let PROXY_USERNAME = url.searchParams.get('proxy_username');
        if (!url.searchParams.has('proxy_password') || url.searchParams.get('proxy_password') === '') return;
        let PROXY_PASSWORD = url.searchParams.get('proxy_password');
        if (!url.searchParams.has('proxy_domains') || url.searchParams.get('proxy_domains') === '') return;
        let PROXY_DOMAINS = url.searchParams.get('proxy_domains');
        if (!url.searchParams.has('proxy_variation') || url.searchParams.get('proxy_variation') === '') return;
        let PROXY_VARIATION = url.searchParams.get('proxy_variation');
        if (!url.searchParams.has('worker_uid') || url.searchParams.get('worker_uid') === '') return;
        let WORKER_UID = url.searchParams.get('worker_uid');
        if (!url.searchParams.has('min_score') || url.searchParams.get('min_score') === '') return;
        let MIN_RECAPTCHA_SCORE = parseInt(url.searchParams.get('min_score'));
        if (!url.searchParams.has('max_score') || url.searchParams.get('max_score') === '') return;
        let MAX_RECAPTCHA_SCORE = parseInt(url.searchParams.get('max_score'));
        if (!url.searchParams.has('api_url') || url.searchParams.get('api_url') === '') return;
        let API_URL = url.searchParams.get('api_url');

        // Construct body of request to obtain new proxy from API
        let rq = {
            WorkerUID: WORKER_UID, MinScore: MIN_RECAPTCHA_SCORE, MaxScore: MAX_RECAPTCHA_SCORE,
            Protocol: PROXY_PROTOCOL, Host: PROXY_HOST, Username: PROXY_USERNAME, Password: PROXY_PASSWORD,
            Domains: PROXY_DOMAINS, Variation: PROXY_VARIATION
        }
        // Send request to API to obtain either cached proxy with high enough score, or a new proxy without any scores yet
        fetch(API_URL + "/get_proxy_details", {
            method: 'POST', body: JSON.stringify(rq),
            headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
        })
            .then((response) => response.json())
            .then((data) => {
                // Generate PAC script by replacing ___DICT___ in it with updated host-to-port mappings
                let newConfig = {mode: "pac_script", pacScript: {data: data.Script}}
                // Set proxy configuration
                chrome.proxy.settings.set({value: newConfig, scope: "regular"}, function () {
                });
                // Save credentials into global variable
                proxyCredentials = {username: data.Username, password: data.Password};
            })
            .catch((error) => {
                console.log('Error during request to obtain proxy details via API: ' + error);
            });
    }
}, {urls: ["<all_urls>"]});

chrome.declarativeNetRequest.onRuleMatchedDebug.addListener((e) => {
});
