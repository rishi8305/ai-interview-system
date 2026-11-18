/**
 * Voice Interview Module
 * Implements Web Speech Recognition (STT) and SpeechSynthesis (TTS).
 * Robust version: handles mic conflicts, auto-restart, interim display.
 */

class VoiceController {
  constructor() {
    this.recognition = null;
    this.isRecording = false;
    this.restartOnEnd = false;
    this.restartTimer = null;
    this.synth = window.speechSynthesis || null;
    this.currentUtterance = null;
    this.isSpeaking = false;
    this.interimBuffer = "";

    this.micBtn = document.getElementById("micToggleBtn");
    this.micStatus = document.getElementById("micStatusText");
    this.waveform = document.getElementById("micWaveform");
    this.answerTextarea = document.getElementById("answerTextarea");
    this.ttsBtn = document.getElementById("ttsReadBtn");
    this.voiceAlert = document.getElementById("voiceSupportAlert");

    this.initSpeechRecognition();
    this.initTextToSpeech();
  }

  initSpeechRecognition() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      this._showAlert(
        "warning",
        "<strong>Voice Input Unavailable:</strong> Your browser does not support the Web Speech API. " +
        "Please use <strong>Chrome</strong> or <strong>Edge</strong> for voice input. You can still type your answers."
      );
      if (this.micBtn) {
        this.micBtn.disabled = true;
        this.micBtn.title = "Speech Recognition not supported in this browser.";
      }
      return;
    }

    this._setupRecognition(SpeechRecognition);

    if (this.micBtn) {
      this.micBtn.addEventListener("click", () => this.toggleRecording());
    }
  }

  _setupRecognition(SpeechRecognition) {
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = "en-US";
    this.recognition.maxAlternatives = 1;

    this.recognition.onstart = () => {
      this.isRecording = true;
      this.interimBuffer = "";
      this.updateMicUI(true);
      console.log("[Voice] Recognition started");
    };

    this.recognition.onresult = (event) => {
      let interimText = "";
      let finalText = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += transcript + " ";
        } else {
          interimText += transcript;
        }
      }

      // Show interim transcript in status (live feedback)
      if (interimText && this.micStatus) {
        this.micStatus.innerHTML =
          `<span class="badge bg-danger text-white px-2 py-1">` +
          `<i class="bi bi-record-circle me-1"></i> Listening...</span> ` +
          `<span class="text-muted fst-italic small">${interimText}</span>`;
      }

      // Append final confirmed speech to textarea
      if (finalText && this.answerTextarea) {
        const current = this.answerTextarea.value;
        this.answerTextarea.value = current
          ? current.trimEnd() + " " + finalText.trim() + " "
          : finalText;
        this.answerTextarea.dispatchEvent(new Event("input"));
        // Reset interim display back to listening badge
        if (this.micStatus) {
          this.micStatus.innerHTML =
            '<span class="badge bg-danger text-white px-2 py-1">' +
            '<i class="bi bi-record-circle me-1"></i> Listening... Speak clearly</span>';
        }
      }
    };

    this.recognition.onerror = (event) => {
      console.warn("[Voice] Recognition error:", event.error);

      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        this._showAlert(
          "danger",
          "<strong>Microphone Permission Denied.</strong> Click the lock/camera icon in your browser address bar and set Microphone to <strong>Allow</strong>, then reload."
        );
        if (this.micStatus) {
          this.micStatus.innerHTML = '<span class="text-danger small"><i class="bi bi-x-circle me-1"></i> Mic blocked in browser settings</span>';
        }
        this.restartOnEnd = false;
        this.isRecording = false;
        this.updateMicUI(false);
        return;
      }

      if (event.error === "audio-capture") {
        this._showAlert(
          "danger",
          "<strong>No Microphone Found.</strong> Make sure your mic is plugged in and enabled in Windows."
        );
        if (this.micStatus) {
          this.micStatus.innerHTML = '<span class="text-danger small"><i class="bi bi-x-circle me-1"></i> No mic detected</span>';
        }
        this.restartOnEnd = false;
        this.isRecording = false;
        this.updateMicUI(false);
        return;
      }

      if (event.error === "network") {
        this._showAlert(
          "warning",
          "<strong>Network / Speech Service:</strong> Speech recognition requires an active internet connection to Google's speech service."
        );
        if (this.micStatus) {
          this.micStatus.innerHTML = '<span class="text-warning small"><i class="bi bi-wifi-off me-1"></i> Network error connecting to speech service</span>';
        }
        this.restartOnEnd = false;
        this.isRecording = false;
        this.updateMicUI(false);
        return;
      }

      if (event.error === "no-speech") {
        if (this.micStatus) {
          this.micStatus.innerHTML =
            '<span class="badge bg-warning text-dark px-2 py-1"><i class="bi bi-mic me-1"></i> Listening... (say something)</span>';
        }
        return;
      }

      if (event.error === "aborted") {
        console.log("[Voice] Recognition aborted.");
        return;
      }

      // Any other error
      if (this.micStatus) {
        this.micStatus.innerHTML = `<span class="text-danger small"><i class="bi bi-exclamation-triangle me-1"></i> Mic error: ${event.error}</span>`;
      }
    };

    this.recognition.onend = () => {
      console.log("[Voice] Recognition ended. restartOnEnd:", this.restartOnEnd);
      if (this.restartOnEnd && this.isRecording) {
        // Debounce restart to avoid rapid loops
        clearTimeout(this.restartTimer);
        this.restartTimer = setTimeout(() => {
          if (this.isRecording) {
            try {
              this.recognition.start();
              console.log("[Voice] Restarted recognition");
            } catch (e) {
              console.warn("[Voice] Restart failed:", e);
              this.isRecording = false;
              this.updateMicUI(false);
            }
          }
        }, 300);
      } else {
        this.isRecording = false;
        this.updateMicUI(false);
      }
    };
  }

  toggleRecording() {
    if (!this.recognition) return;
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording();
    }
  }

  startRecording() {
    if (!this.recognition) return;

    // Stop TTS if speaking — mic and TTS conflict
    if (this.synth && this.synth.speaking) {
      this.synth.cancel();
      this.updateTtsUI(false);
    }

    this.restartOnEnd = true;
    this.isRecording = true;

    try {
      this.recognition.start();
      this.updateMicUI(true);
    } catch (e) {
      // If already started or pending, handle gracefully
      console.warn("[Voice] Start error:", e.message);
      if (e.name === "InvalidStateError") {
        // Recognition already started, keep UI in sync
        this.updateMicUI(true);
      } else {
        this.isRecording = false;
        this.updateMicUI(false);
      }
    }
  }

  stopRecording() {
    this.restartOnEnd = false;
    this.isRecording = false;
    clearTimeout(this.restartTimer);

    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }
    this.updateMicUI(false);
  }

  updateMicUI(recording) {
    if (!this.micBtn) return;

    if (recording) {
      this.micBtn.className = "pulse-mic";
      this.micBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
      this.micBtn.title = "Click to stop voice input";
      if (this.micStatus) {
        this.micStatus.innerHTML =
          '<span class="badge bg-danger text-white px-2 py-1">' +
          '<i class="bi bi-record-circle me-1"></i> Listening... Speak clearly</span>';
      }
      if (this.waveform) this.waveform.classList.remove("d-none");
    } else {
      this.micBtn.className = "pulse-mic mic-inactive";
      this.micBtn.innerHTML = '<i class="bi bi-mic-mute-fill"></i>';
      this.micBtn.title = "Click microphone to start voice input";
      if (this.micStatus) {
        this.micStatus.innerHTML =
          '<span class="text-muted"><i class="bi bi-mic me-1"></i> Click microphone to start voice input</span>';
      }
      if (this.waveform) this.waveform.classList.add("d-none");
    }
  }

  _showAlert(type, html) {
    if (!this.voiceAlert) return;
    this.voiceAlert.classList.remove("d-none", "alert-warning", "alert-danger", "alert-info");
    this.voiceAlert.classList.add(`alert-${type}`);
    this.voiceAlert.innerHTML = `<i class="bi bi-info-circle-fill me-2"></i>${html}`;
  }

  /* --- TEXT-TO-SPEECH (TTS) QUESTION READER --- */
  initTextToSpeech() {
    if (!this.ttsBtn || !this.synth) return;
    this.ttsBtn.addEventListener("click", () => this.toggleSpeech());
  }

  toggleSpeech() {
    if (!this.synth) return;

    // Stop mic when TTS starts (they conflict)
    if (this.isRecording) {
      this.stopRecording();
    }

    if (this.synth.speaking) {
      this.synth.cancel();
      this.isSpeaking = false;
      this.updateTtsUI(false);
      return;
    }

    const questionTextEl = document.getElementById("questionText");
    if (!questionTextEl) return;

    const textToRead = questionTextEl.innerText.trim();
    if (!textToRead) return;

    this.currentUtterance = new SpeechSynthesisUtterance(textToRead);
    this.currentUtterance.rate = 0.92;
    this.currentUtterance.pitch = 1.0;
    this.currentUtterance.lang = "en-US";

    this.currentUtterance.onstart = () => {
      this.isSpeaking = true;
      this.updateTtsUI(true);
    };
    this.currentUtterance.onend = () => {
      this.isSpeaking = false;
      this.updateTtsUI(false);
    };
    this.currentUtterance.onerror = () => {
      this.isSpeaking = false;
      this.updateTtsUI(false);
    };

    this.synth.speak(this.currentUtterance);
  }

  updateTtsUI(speaking) {
    if (!this.ttsBtn) return;
    if (speaking) {
      this.ttsBtn.innerHTML = '<i class="bi bi-stop-circle-fill me-1"></i> Stop Audio';
      this.ttsBtn.classList.replace("btn-outline-primary", "btn-danger");
    } else {
      this.ttsBtn.innerHTML = '<i class="bi bi-volume-up-fill me-1"></i> Read Aloud';
      this.ttsBtn.classList.replace("btn-danger", "btn-outline-primary");
    }
  }
}

// Instantiate on interview page
document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("answerTextarea")) {
    window.voiceController = new VoiceController();
  }
});
