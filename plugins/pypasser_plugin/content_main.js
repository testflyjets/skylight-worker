console.log("[content_main.js] Main site script running...");

chrome.storage.local.get("audioLink", ({ audioLink }) => {
  if (audioLink) {
    document.cookie = `audio_src=${audioLink}; path=/; max-age=300;`;
    console.log("Кука установлена в основном окне:", audioLink);
  } else {
    console.log("Нет audioLink в storage");
  }
});
