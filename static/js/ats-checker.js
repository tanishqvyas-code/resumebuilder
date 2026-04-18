(() => {
  "use strict";

  const fileInput = document.getElementById("pdf-file");
  const targetRoleInput = document.getElementById("pdf-target-role");
  const jdInput = document.getElementById("pdf-job-description");
  const btn = document.getElementById("btn-pdf-ats-check");
  const reportEl = document.getElementById("pdf-ats-report");
  const toastEl = document.getElementById("toast");

  function showToast(msg, isError = false) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    toastEl.style.borderColor = isError ? "#7f1d1d" : "var(--border)";
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => {
      toastEl.hidden = true;
    }, 4200);
  }

  function esc(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function renderReport(data) {
    const strengths = (data.strengths || []).map((s) => `<li>${esc(s)}</li>`).join("");
    const concerns = (data.concerns || []).map((s) => `<li>${esc(s)}</li>`).join("");
    const suggestions = (data.suggestions || []).map((s) => `<li>${esc(s)}</li>`).join("");
    const breakdown = (data.breakdown || [])
      .map((b) => `<div class="ats-breakdown-item"><strong>${esc(b.name)}:</strong> ${b.score}/${b.max} - ${esc(b.detail || "")}</div>`)
      .join("");

    reportEl.innerHTML = `
      <div class="ats-score-line">
        <div class="ats-score-value">${Number(data.score || 0)}/100</div>
        <div class="ats-rating">${esc(data.rating || "Unrated")}</div>
      </div>
      <div>${breakdown}</div>
      <h3 style="margin:10px 0 4px;font-size:0.95rem;">Strengths</h3>
      <ul class="ats-list">${strengths || "<li>No strengths detected yet.</li>"}</ul>
      <h3 style="margin:10px 0 4px;font-size:0.95rem;">Concerns</h3>
      <ul class="ats-list">${concerns || "<li>No major concerns detected.</li>"}</ul>
      <h3 style="margin:10px 0 4px;font-size:0.95rem;">Actionable fixes</h3>
      <ul class="ats-list">${suggestions || "<li>Tailor role keywords and quantify outcomes.</li>"}</ul>
      <p class="ats-note">${esc(data.honesty_note || "")}</p>
    `;
    reportEl.hidden = false;
  }

  btn.addEventListener("click", async () => {
    try {
      const file = fileInput.files && fileInput.files[0];
      if (!file) {
        showToast("Please upload a PDF file.", true);
        return;
      }
      btn.disabled = true;
      const fd = new FormData();
      fd.append("file", file);
      fd.append("target_role", targetRoleInput.value.trim());
      fd.append("job_description", jdInput.value.trim());

      const res = await fetch("/api/ai/ats-score-upload", {
        method: "POST",
        body: fd,
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || res.statusText || "ATS score check failed");
      }
      renderReport(body);
      showToast("ATS score generated from uploaded PDF.");
    } catch (e) {
      showToast(e.message || "ATS score check failed", true);
    } finally {
      btn.disabled = false;
    }
  });
})();
