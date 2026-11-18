/**
 * Live Interview Engine UI Controller
 */

document.addEventListener("DOMContentLoaded", function () {
  const answerTextarea = document.getElementById("answerTextarea");
  const wordCountSpan = document.getElementById("wordCount");
  const charCountSpan = document.getElementById("charCount");
  const submitBtn = document.getElementById("submitAnswerBtn");
  const evalOverlay = document.getElementById("evalOverlay");
  const evalStatusMsg = document.getElementById("evalStatusMsg");
  const interviewTimerEl = document.getElementById("interviewTimer");
  const interviewForm = document.getElementById("interviewForm");

  // Word & Character Counter
  if (answerTextarea && wordCountSpan && charCountSpan) {
    answerTextarea.addEventListener("input", function () {
      const text = this.value.trim();
      const words = text ? text.split(/\s+/).length : 0;
      wordCountSpan.innerText = words;
      charCountSpan.innerText = text.length;
    });
  }

  // Live Timer
  if (interviewTimerEl) {
    let secondsElapsed = 0;
    setInterval(function () {
      secondsElapsed++;
      const mins = Math.floor(secondsElapsed / 60);
      const secs = secondsElapsed % 60;
      interviewTimerEl.innerText = `${mins.toString().padStart(2, "0")}:${secs
        .toString()
        .padStart(2, "0")}`;
    }, 1000);
  }

  // Answer Submission via AJAX
  if (submitBtn && interviewForm) {
    submitBtn.addEventListener("click", function (e) {
      e.preventDefault();
      submitCurrentAnswer();
    });

    // Keyboard shortcut: Ctrl+Enter or Cmd+Enter
    if (answerTextarea) {
      answerTextarea.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
          e.preventDefault();
          submitCurrentAnswer();
        }
      });
    }
  }

  function submitCurrentAnswer() {
    const questionId = document.getElementById("questionId")?.value;
    const answerText = answerTextarea ? answerTextarea.value.trim() : "";
    const submitUrl = interviewForm?.getAttribute("action");

    if (!submitUrl || !questionId) {
      console.error("Missing submit URL or question ID");
      return;
    }

    if (!answerText) {
      const proceed = confirm(
        "You have not typed or spoken an answer. Submitting an empty response will yield a score of 0 for this question. Do you wish to continue?"
      );
      if (!proceed) return;
    }

    // Stop voice recording if running
    if (window.voiceController && window.voiceController.isRecording) {
      window.voiceController.stopRecording();
    }

    // Disable button to prevent duplicate submissions
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Submitting...';

    // Show AI Evaluation Loading Screen
    if (evalOverlay) {
      evalOverlay.style.display = "flex";
      animateEvaluationSteps();
    }

    fetch(submitUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({
        question_id: questionId,
        answer_text: answerText,
      }),
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Submission failed. Please try again.");
        }
        return data;
      })
      .then((data) => {
        if (data.redirect) {
          window.location.href = data.redirect;
        } else {
          window.location.reload();
        }
      })
      .catch((error) => {
        console.error("Submission error:", error);
        alert(error.message || "An error occurred while evaluating your response.");
        if (evalOverlay) evalOverlay.style.display = "none";
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-arrow-right-circle-fill me-2"></i> Submit & Next';
      });
  }

  function animateEvaluationSteps() {
    if (!evalStatusMsg) return;

    const messages = [
      "Analyzing response against standard technical rubric...",
      "Evaluating Technical Correctness (40% weight)...",
      "Measuring Relevance (25%) and Completeness (20%)...",
      "Assessing Communication Clarity (15%)...",
      "Generating personalized constructive feedback...",
      "Finalizing score and preparing next question...",
    ];

    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % messages.length;
      if (evalStatusMsg) {
        evalStatusMsg.innerText = messages[idx];
      }
    }, 1800);
  }
});
