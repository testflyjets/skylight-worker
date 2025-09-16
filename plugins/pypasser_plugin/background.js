window.addEventListener("message", (event) => {
  if (event.data?.type === "AUDIO_SRC") {
    console.log("Получено из iframe:", event.data.value);
    localStorage.setItem("audio_src", event.data.value);
  }
});


