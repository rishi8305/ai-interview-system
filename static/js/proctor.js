/**
 * AI Interview Proctoring & Integrity Engine
 * Handles webcam stream, face configuration, tab-switch monitoring,
 * prohibited object / multiple person detection, and penalty alerts.
 */

class ProctorEngine {
  constructor() {
    this.video = document.getElementById("proctorVideo");
    this.faceConfigVideo = document.getElementById("faceConfigVideo");
    this.statusBadge = document.getElementById("proctorStatusBadge");
    this.tabSwitchBadge = document.getElementById("proctorTabBadge");
    this.proctorAlertModal = document.getElementById("proctorAlertModal");
    this.proctorAlertMsg = document.getElementById("proctorAlertMsg");

    this.stream = null;
    this.tabSwitchCount = 0;
    this.lastTabSwitchTime = 0;
    this.interviewId = this.getInterviewId();

    this.cocoModel = null;
    this.isAnalyzing = false;
    this.audioCtx = null;

    this.initAudioContext();
    this.initWebcam();
    this.initTabSwitchMonitoring();
    this.loadObjectDetectionModel();
  }

  getInterviewId() {
    const form = document.getElementById("interviewForm");
    if (form) {
      const match = form.action.match(/\/interview\/(\d+)\//);
      if (match) return match[1];
    }
    const pathMatch = window.location.pathname.match(/\/interview\/(\d+)\//);
    return pathMatch ? pathMatch[1] : null;
  }

  initAudioContext() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.audioCtx = new AudioCtx();
      }
    } catch (e) {
      console.warn("AudioContext not supported", e);
    }
  }

  playWarningBeep() {
    if (!this.audioCtx) return;
    try {
      if (this.audioCtx.state === "suspended") {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(440, this.audioCtx.currentTime); // A4
      osc.frequency.exponentialRampToValueAtTime(880, this.audioCtx.currentTime + 0.3); // Ramp to A5
      gain.gain.setValueAtTime(0.3, this.audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioCtx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start();
      osc.stop(this.audioCtx.currentTime + 0.35);
    } catch (e) {}
  }

  /* --- WEBCAM INITIALIZATION & FACE CONFIGURATION --- */
  async initWebcam() {
    const targetVideo = this.video || this.faceConfigVideo;
    if (!targetVideo) return;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false,
      });
      targetVideo.srcObject = this.stream;
      await targetVideo.play();

      if (this.statusBadge) {
        this.statusBadge.className = "badge bg-success";
        this.statusBadge.innerHTML = '<i class="bi bi-person-check-fill me-1"></i> Proctoring Active';
      }

      // If on live interview page, start periodic frame analysis
      if (this.video && this.interviewId) {
        setInterval(() => this.analyzeCurrentFrame(), 3000);
      }
    } catch (err) {
      console.warn("Camera access denied or unavailable:", err);
      if (this.statusBadge) {
        this.statusBadge.className = "badge bg-danger";
        this.statusBadge.innerHTML = '<i class="bi bi-camera-video-off-fill me-1"></i> Camera Required';
      }
      const setupFeedback = document.getElementById("cameraSetupFeedback");
      if (setupFeedback) {
        setupFeedback.innerHTML = `
          <div class="alert alert-danger small mb-0">
            <i class="bi bi-exclamation-triangle-fill me-1"></i> Camera permission was denied. Please allow camera permissions in your browser address bar.
          </div>
        `;
      }
    }
  }

  /* --- TAB SWITCH & BLUR DETECTION --- */
  initTabSwitchMonitoring() {
    if (!this.interviewId) return;

    // Visibility Change (User switches tabs or minimizes)
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        this.handleTabSwitch("Candidate navigated away from the interview tab.");
      }
    });

    // Window Blur (User clicks on another window or devtools)
    window.addEventListener("blur", () => {
      this.handleTabSwitch("Candidate clicked outside the active interview window.");
    });
  }

  handleTabSwitch(reason) {
    const now = Date.now();
    // Debounce to prevent duplicate triggers within 2 seconds
    if (now - this.lastTabSwitchTime < 2000) return;
    this.lastTabSwitchTime = now;

    this.tabSwitchCount++;
    this.playWarningBeep();

    // Log to server
    fetch(`/interview/${this.interviewId}/proctor/tab_switch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((res) => res.json())
      .then((data) => {
        const totalPenalty = data.penalty_percentage || this.tabSwitchCount * 5;
        this.updateTabUI(data.tab_switches || this.tabSwitchCount, totalPenalty);
        this.showTabWarningModal(data.tab_switches || this.tabSwitchCount, totalPenalty);
      })
      .catch((err) => {
        console.warn("Tab switch log error:", err);
        const penalty = this.tabSwitchCount * 5;
        this.updateTabUI(this.tabSwitchCount, penalty);
        this.showTabWarningModal(this.tabSwitchCount, penalty);
      });
  }

  updateTabUI(count, penaltyPct) {
    if (this.tabSwitchBadge) {
      this.tabSwitchBadge.className = "badge bg-danger";
      this.tabSwitchBadge.innerHTML = `<i class="bi bi-exclamation-octagon-fill me-1"></i> Tab Switches: ${count} (-${penaltyPct}%)`;
    }
  }

  showTabWarningModal(count, penaltyPct) {
    if (this.proctorAlertMsg) {
      this.proctorAlertMsg.innerHTML = `
        <div class="text-danger mb-2 fs-5 fw-bold">
          <i class="bi bi-exclamation-triangle-fill me-2"></i> Tab Switch Detected! (#${count})
        </div>
        <p class="mb-2 text-dark">
          You navigated away from the interview interface. Per integrity regulations, a <strong>5% mark deduction</strong> has been applied to your score.
        </p>
        <div class="p-2 bg-danger-subtle text-danger rounded small fw-semibold">
          Total Proctoring Deduction: -${penaltyPct}% from final score.
        </div>
      `;
    }

    if (this.proctorAlertModal) {
      const modal = new bootstrap.Modal(this.proctorAlertModal);
      modal.show();
    } else {
      alert(`⚠️ PROCTORING ALERT: Tab switch detected (Occurrence #${count}). A 5% score penalty has been applied.`);
    }
  }

  /* --- OBJECT & MULTIPLE PERSON DETECTION --- */
  async loadObjectDetectionModel() {
    try {
      if (window.cocoSsd) {
        this.cocoModel = await window.cocoSsd.load();
        console.log("COCO-SSD Object detection model loaded.");
      }
    } catch (e) {
      console.warn("COCO-SSD CDN unavailable, relying on OpenCV server analyzer:", e);
    }
  }

  async analyzeCurrentFrame() {
    if (!this.video || this.isAnalyzing) return;
    this.isAnalyzing = true;

    try {
      // 1. Client-Side COCO-SSD check if model is loaded
      if (this.cocoModel && this.video.readyState === 4) {
        const predictions = await this.cocoModel.detect(this.video);
        let personCount = 0;
        let prohibitedObjects = [];

        predictions.forEach((pred) => {
          if (pred.class === "person" && pred.score > 0.5) {
            personCount++;
          }
          if (["cell phone", "laptop", "remote", "book"].includes(pred.class) && pred.score > 0.5) {
            prohibitedObjects.push(pred.class);
          }
        });

        if (personCount > 1) {
          this.triggerViolation(
            "multiple_faces",
            `Multiple people (${personCount} persons) detected in camera frame!`,
            "high"
          );
        } else if (prohibitedObjects.length > 0) {
          this.triggerViolation(
            "prohibited_object",
            `Prohibited object (${prohibitedObjects.join(", ")}) detected in camera view!`,
            "high"
          );
        } else if (personCount === 0) {
          this.updateBadgeStatus("no_face", "Candidate not visible in frame", "warning");
        } else {
          this.updateBadgeStatus("verified", "Face Verified (1 Person)", "success");
        }
      } else {
        // 2. Server-Side OpenCV Fallback Analysis
        await this.sendFrameToServer();
      }
    } catch (e) {
      console.warn("Frame analysis error:", e);
    } finally {
      this.isAnalyzing = false;
    }
  }

  async sendFrameToServer() {
    if (!this.video || this.video.readyState !== 4) return;

    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
    const base64Data = canvas.toDataURL("image/jpeg", 0.6);

    try {
      const res = await fetch(`/interview/${this.interviewId}/proctor/analyze_frame`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64Data }),
      });
      const data = await res.json();

      if (data.violation) {
        this.triggerViolation(data.status, data.message, data.severity);
      } else {
        this.updateBadgeStatus("verified", "Face Verified (1 Person)", "success");
      }
    } catch (e) {}
  }

  triggerViolation(type, msg, severity) {
    this.playWarningBeep();
    this.updateBadgeStatus(type, msg, severity === "high" ? "danger" : "warning");

    // Report event to backend if not already reported recently
    const now = Date.now();
    if (now - (this.lastViolationReportTime || 0) > 8000) {
      this.lastViolationReportTime = now;
      fetch(`/interview/${this.interviewId}/proctor/log_event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: type,
          description: msg,
          severity: severity,
        }),
      }).catch((e) => {});
    }
  }

  updateBadgeStatus(type, text, level) {
    if (!this.statusBadge) return;
    this.statusBadge.className = `badge bg-${level}`;
    const icon = level === "danger" ? "exclamation-triangle-fill" : (level === "warning" ? "eye-slash-fill" : "person-check-fill");
    this.statusBadge.innerHTML = `<i class="bi bi-${icon} me-1"></i> ${text}`;
  }
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  window.proctorEngine = new ProctorEngine();
});
