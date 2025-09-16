async function getConfig() {
  const res = await fetch(chrome.runtime.getURL('config.json'));
  return await res.json();
}

getConfig().then(config => {
  const BACKEND_URL = config.backend_url;

  const sendAudioLink = (audio, downloadButton, decodeInput) => {
    if (!audio || !audio.src || audio.src.trim() === "") {
      console.log("[recaptcha_sender.js] Audio src is empty or invalid.");
      return;
    }

    const parentDomain = document.location.ancestorOrigins.length
      ? document.location.ancestorOrigins[document.location.ancestorOrigins.length - 1]
      : "unknown";

    fetch(`${BACKEND_URL}/captcha_audio_link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        link: audio.src,
        hasDownloadButton: !!downloadButton,
        validCaptcha: decodeInput,
        domain: parentDomain
      })
    })
    .then(res => res.json())
    .then(data => {
      console.log("[recaptcha_sender.js] Key received:", data.key);
    })
    .catch(err => {
      console.error("[recaptcha_sender.js] Error sending audio link:", err);
    });
  };

  const observer = new MutationObserver(() => {
    const audio = document.getElementById("audio-source");
    const downloadButton = document.querySelector("#rc-audio > div.rc-audiochallenge-tdownload > a");
    const decodeInput = document.querySelector("#audio-response") !== null;

    if (audio) {
      const checkSrcInterval = setInterval(() => {
        if (audio.src && audio.src.trim() !== "") {
          console.log("[recaptcha_sender.js] Audio src detected:", audio.src);
          sendAudioLink(audio, downloadButton, decodeInput);
          clearInterval(checkSrcInterval);
          observer.disconnect();
        } else {
          console.log("[recaptcha_sender.js] Waiting for audio src...");
        }
      }, 500);

      setTimeout(() => {
        clearInterval(checkSrcInterval);
        console.warn("[recaptcha_sender.js] Timeout waiting for audio src.");
      }, 10000);
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
});
