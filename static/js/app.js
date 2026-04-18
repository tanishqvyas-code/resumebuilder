(() => {
  "use strict";

  const saveStatusEl = document.getElementById("save-status");
  const previewFrame = document.getElementById("preview-frame");
  const form = document.getElementById("resume-form");
  const toastEl = document.getElementById("toast");

  const containers = {
    skills: document.getElementById("skills-list"),
    work: document.getElementById("work-list"),
    education: document.getElementById("education-list"),
    projects: document.getElementById("projects-list"),
    certs: document.getElementById("certs-list"),
    achievements: document.getElementById("achievements-list"),
    languages: document.getElementById("languages-list"),
  };

  /** @type {any} */
  let state = emptyResume();
  let saveTimer = null;
  let previewTimer = null;
  let sessionReady = false;

  function emptyResume() {
    return {
      personal: {
        full_name: "",
        phone: "",
        email: "",
        linkedin_url: "",
        portfolio_url: "",
        location: "",
      },
      professional_summary: "",
      skills: [],
      work_experience: [],
      education: [],
      projects: [],
      certifications: [],
      achievements: [],
      languages: [],
    };
  }

  function showToast(msg, isError = false) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    toastEl.style.borderColor = isError ? "#7f1d1d" : "var(--border)";
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => {
      toastEl.hidden = true;
    }, 4200);
  }

  function setSaveStatus(text) {
    saveStatusEl.textContent = text;
  }

  async function apiFetch(path, options = {}) {
    const opts = {
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    };
    let res = await fetch(path, opts);
    if (res.status === 401) {
      await ensureSession();
      res = await fetch(path, opts);
    }
    return res;
  }

  async function ensureSession() {
    const res = await fetch("/api/session", {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) throw new Error("Could not create session");
    sessionReady = true;
    return res.json();
  }

  function renderSkills() {
    containers.skills.innerHTML = "";
    state.skills.forEach((cat, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block skill-cat";
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Skill category ${idx + 1}</div>
          <button type="button" class="btn danger small" data-remove-skill="${idx}">Remove</button>
        </div>
        <label>Category name
          <input type="text" class="sk-cat-name" value="${escapeAttr(cat.category_name)}" placeholder="e.g. Technical Skills" />
        </label>
        <label>Skills (comma-separated)
          <textarea class="sk-cat-items" rows="3" placeholder="Python, SQL, AWS">${escapeHtml(cat.items.join(", "))}</textarea>
        </label>
      `;
      containers.skills.appendChild(wrap);
    });
    containers.skills.querySelectorAll("[data-remove-skill]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-skill"));
        state.skills.splice(i, 1);
        renderSkills();
        scheduleSaveAndPreview();
      });
    });
  }

  function renderWork() {
    containers.work.innerHTML = "";
    state.work_experience.forEach((job, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block work-item";
      const bullets = (job.bullets || []).map((b) => escapeHtml(b)).join("\n");
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Position ${idx + 1}</div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button type="button" class="btn small" data-ai-work="${idx}">AI: improve bullets</button>
            <button type="button" class="btn danger small" data-remove-work="${idx}">Remove</button>
          </div>
        </div>
        <div class="grid2">
          <label>Job title<input type="text" class="w-title" value="${escapeAttr(job.job_title)}" /></label>
          <label>Company<input type="text" class="w-company" value="${escapeAttr(job.company_name)}" /></label>
          <label>Location<input type="text" class="w-loc" value="${escapeAttr(job.location)}" /></label>
          <label>Start date<input type="text" class="w-start" value="${escapeAttr(job.start_date)}" placeholder="YYYY-MM" /></label>
          <label>End date<input type="text" class="w-end" value="${escapeAttr(job.end_date)}" placeholder="YYYY-MM or Present" /></label>
        </div>
        <label>Bullets (one per line)<textarea class="w-bullets" rows="5" placeholder="Led ...">${bullets}</textarea></label>
      `;
      containers.work.appendChild(wrap);
    });
    containers.work.querySelectorAll("[data-remove-work]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-work"));
        state.work_experience.splice(i, 1);
        renderWork();
        scheduleSaveAndPreview();
      });
    });
    containers.work.querySelectorAll("[data-ai-work]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const i = Number(btn.getAttribute("data-ai-work"));
        collectFromDom();
        const job = state.work_experience[i];
        if (!job) return;
        btn.disabled = true;
        try {
          const res = await apiFetch("/api/ai/bullets", {
            method: "POST",
            body: JSON.stringify({
              context: `${job.job_title || ""} at ${job.company_name || ""}`.trim(),
              bullets: (job.bullets || []).filter(Boolean),
            }),
          });
          if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
          const data = await res.json();
          state.work_experience[i].bullets = data.bullets && data.bullets.length ? data.bullets : job.bullets;
          renderWork();
          scheduleSaveAndPreview();
          showToast("Bullets updated.");
        } catch (e) {
          showToast(e.message || "AI request failed", true);
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function renderEducation() {
    containers.education.innerHTML = "";
    state.education.forEach((ed, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block";
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Education ${idx + 1}</div>
          <button type="button" class="btn danger small" data-remove-edu="${idx}">Remove</button>
        </div>
        <div class="grid2">
          <label>Degree<input type="text" class="e-degree" value="${escapeAttr(ed.degree)}" /></label>
          <label>Institution<input type="text" class="e-inst" value="${escapeAttr(ed.institution)}" /></label>
          <label>Location<input type="text" class="e-loc" value="${escapeAttr(ed.location)}" /></label>
          <label>Graduation year<input type="text" class="e-year" value="${escapeAttr(ed.graduation_year)}" /></label>
          <label>GPA (optional)<input type="text" class="e-gpa" value="${escapeAttr(ed.gpa || "")}" /></label>
        </div>
      `;
      containers.education.appendChild(wrap);
    });
    containers.education.querySelectorAll("[data-remove-edu]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-edu"));
        state.education.splice(i, 1);
        renderEducation();
        scheduleSaveAndPreview();
      });
    });
  }

  function renderProjects() {
    containers.projects.innerHTML = "";
    state.projects.forEach((pr, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block";
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Project ${idx + 1}</div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button type="button" class="btn small" data-ai-proj="${idx}">AI: enhance description</button>
            <button type="button" class="btn danger small" data-remove-proj="${idx}">Remove</button>
          </div>
        </div>
        <label>Title<input type="text" class="p-title" value="${escapeAttr(pr.title)}" /></label>
        <label>Technologies<input type="text" class="p-tech" value="${escapeAttr(pr.technologies_used)}" /></label>
        <label>Description<textarea class="p-desc" rows="4">${escapeHtml(pr.description)}</textarea></label>
        <label>Link (optional)<input type="url" class="p-link" value="${escapeAttr(pr.link)}" /></label>
      `;
      containers.projects.appendChild(wrap);
    });
    containers.projects.querySelectorAll("[data-remove-proj]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-proj"));
        state.projects.splice(i, 1);
        renderProjects();
        scheduleSaveAndPreview();
      });
    });
    containers.projects.querySelectorAll("[data-ai-proj]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const i = Number(btn.getAttribute("data-ai-proj"));
        collectFromDom();
        const pr = state.projects[i];
        if (!pr) return;
        btn.disabled = true;
        try {
          const res = await apiFetch("/api/ai/project-description", {
            method: "POST",
            body: JSON.stringify({
              text: pr.description || "",
              technologies: pr.technologies_used || "",
              context: pr.title || "Project",
            }),
          });
          if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
          const data = await res.json();
          state.projects[i].description = data.description || pr.description;
          renderProjects();
          scheduleSaveAndPreview();
          showToast("Project description updated.");
        } catch (e) {
          showToast(e.message || "AI request failed", true);
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function renderCerts() {
    containers.certs.innerHTML = "";
    state.certifications.forEach((c, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block";
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Certification ${idx + 1}</div>
          <button type="button" class="btn danger small" data-remove-cert="${idx}">Remove</button>
        </div>
        <div class="grid2">
          <label>Name<input type="text" class="c-name" value="${escapeAttr(c.name)}" /></label>
          <label>Issuer<input type="text" class="c-issuer" value="${escapeAttr(c.issuer)}" /></label>
          <label>Date<input type="text" class="c-date" value="${escapeAttr(c.date)}" /></label>
        </div>
      `;
      containers.certs.appendChild(wrap);
    });
    containers.certs.querySelectorAll("[data-remove-cert]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-cert"));
        state.certifications.splice(i, 1);
        renderCerts();
        scheduleSaveAndPreview();
      });
    });
  }

  function renderAchievements() {
    containers.achievements.innerHTML = "";
    state.achievements.forEach((line, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block";
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Achievement ${idx + 1}</div>
          <button type="button" class="btn danger small" data-remove-ach="${idx}">Remove</button>
        </div>
        <label>Bullet<input type="text" class="a-line" value="${escapeAttr(line)}" /></label>
      `;
      containers.achievements.appendChild(wrap);
    });
    containers.achievements.querySelectorAll("[data-remove-ach]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-ach"));
        state.achievements.splice(i, 1);
        renderAchievements();
        scheduleSaveAndPreview();
      });
    });
  }

  function renderLanguages() {
    containers.languages.innerHTML = "";
    state.languages.forEach((lang, idx) => {
      const wrap = document.createElement("div");
      wrap.className = "dynamic-block";
      wrap.innerHTML = `
        <div class="dynamic-head">
          <div class="dynamic-title">Language ${idx + 1}</div>
          <button type="button" class="btn danger small" data-remove-lang="${idx}">Remove</button>
        </div>
        <div class="grid2">
          <label>Language<input type="text" class="l-name" value="${escapeAttr(lang.language)}" /></label>
          <label>Proficiency<input type="text" class="l-prof" value="${escapeAttr(lang.proficiency)}" placeholder="Native / Professional / Basic" /></label>
        </div>
      `;
      containers.languages.appendChild(wrap);
    });
    containers.languages.querySelectorAll("[data-remove-lang]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = Number(btn.getAttribute("data-remove-lang"));
        state.languages.splice(i, 1);
        renderLanguages();
        scheduleSaveAndPreview();
      });
    });
  }

  function renderDynamics() {
    renderSkills();
    renderWork();
    renderEducation();
    renderProjects();
    renderCerts();
    renderAchievements();
    renderLanguages();
  }

  function applyPersonalToDom() {
    const p = state.personal;
    form.elements.full_name.value = p.full_name || "";
    form.elements.location.value = p.location || "";
    form.elements.email.value = p.email || "";
    form.elements.phone.value = p.phone || "";
    form.elements.linkedin_url.value = p.linkedin_url || "";
    form.elements.portfolio_url.value = p.portfolio_url || "";
    form.elements.professional_summary.value = state.professional_summary || "";
  }

  function collectFromDom() {
    state.personal = {
      full_name: form.elements.full_name.value.trim(),
      location: form.elements.location.value.trim(),
      email: form.elements.email.value.trim(),
      phone: form.elements.phone.value.trim(),
      linkedin_url: form.elements.linkedin_url.value.trim(),
      portfolio_url: form.elements.portfolio_url.value.trim(),
    };
    state.professional_summary = form.elements.professional_summary.value;

    state.skills = [...containers.skills.querySelectorAll(".skill-cat")].map((el) => {
      const name = el.querySelector(".sk-cat-name")?.value?.trim() || "";
      const raw = el.querySelector(".sk-cat-items")?.value || "";
      const items = raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      return { category_name: name, items };
    });

    state.work_experience = [...containers.work.querySelectorAll(".work-item")].map((el) => {
      const bulletsRaw = el.querySelector(".w-bullets")?.value || "";
      const bullets = bulletsRaw
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      return {
        job_title: el.querySelector(".w-title")?.value?.trim() || "",
        company_name: el.querySelector(".w-company")?.value?.trim() || "",
        location: el.querySelector(".w-loc")?.value?.trim() || "",
        start_date: el.querySelector(".w-start")?.value?.trim() || "",
        end_date: el.querySelector(".w-end")?.value?.trim() || "",
        bullets,
      };
    });

    state.education = [...containers.education.querySelectorAll(".dynamic-block")].map((el) => ({
      degree: el.querySelector(".e-degree")?.value?.trim() || "",
      institution: el.querySelector(".e-inst")?.value?.trim() || "",
      location: el.querySelector(".e-loc")?.value?.trim() || "",
      graduation_year: el.querySelector(".e-year")?.value?.trim() || "",
      gpa: el.querySelector(".e-gpa")?.value?.trim() || undefined,
    }));

    state.projects = [...containers.projects.querySelectorAll(".dynamic-block")].map((el) => ({
      title: el.querySelector(".p-title")?.value?.trim() || "",
      technologies_used: el.querySelector(".p-tech")?.value?.trim() || "",
      description: el.querySelector(".p-desc")?.value?.trim() || "",
      link: el.querySelector(".p-link")?.value?.trim() || "",
    }));

    state.certifications = [...containers.certs.querySelectorAll(".dynamic-block")].map((el) => ({
      name: el.querySelector(".c-name")?.value?.trim() || "",
      issuer: el.querySelector(".c-issuer")?.value?.trim() || "",
      date: el.querySelector(".c-date")?.value?.trim() || "",
    }));

    state.achievements = [...containers.achievements.querySelectorAll(".a-line")]
      .map((i) => i.value.trim())
      .filter(Boolean);

    state.languages = [...containers.languages.querySelectorAll(".dynamic-block")].map((el) => ({
      language: el.querySelector(".l-name")?.value?.trim() || "",
      proficiency: el.querySelector(".l-prof")?.value?.trim() || "",
    }));
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replaceAll("\n", " ");
  }

  async function saveResume() {
    collectFromDom();
    setSaveStatus("Saving…");
    try {
      const res = await apiFetch("/api/resume", {
        method: "PUT",
        body: JSON.stringify(state),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      setSaveStatus("Saved");
    } catch (e) {
      setSaveStatus("Save failed");
      showToast(e.message || "Save failed", true);
    }
  }

  async function refreshPreview() {
    try {
      const res = await apiFetch("/api/export/html", { method: "GET" });
      if (!res.ok) return;
      const html = await res.text();
      previewFrame.srcdoc = html;
    } catch {
      /* ignore preview errors */
    }
  }

  function scheduleSaveAndPreview() {
    clearTimeout(saveTimer);
    clearTimeout(previewTimer);
    setSaveStatus("Editing…");
    saveTimer = setTimeout(async () => {
      await saveResume();
      previewTimer = setTimeout(refreshPreview, 120);
    }, 650);
  }

  form.addEventListener("input", () => scheduleSaveAndPreview());

  document.getElementById("add-skill-cat").addEventListener("click", () => {
    collectFromDom();
    state.skills.push({ category_name: "", items: [] });
    renderSkills();
    scheduleSaveAndPreview();
  });

  document.getElementById("add-work").addEventListener("click", () => {
    collectFromDom();
    state.work_experience.push({
      job_title: "",
      company_name: "",
      location: "",
      start_date: "",
      end_date: "",
      bullets: [],
    });
    renderWork();
    scheduleSaveAndPreview();
  });

  document.getElementById("add-education").addEventListener("click", () => {
    collectFromDom();
    state.education.push({
      degree: "",
      institution: "",
      location: "",
      graduation_year: "",
      gpa: null,
    });
    renderEducation();
    scheduleSaveAndPreview();
  });

  document.getElementById("add-project").addEventListener("click", () => {
    collectFromDom();
    state.projects.push({
      title: "",
      description: "",
      technologies_used: "",
      link: "",
    });
    renderProjects();
    scheduleSaveAndPreview();
  });

  document.getElementById("add-cert").addEventListener("click", () => {
    collectFromDom();
    state.certifications.push({ name: "", issuer: "", date: "" });
    renderCerts();
    scheduleSaveAndPreview();
  });

  document.getElementById("add-achievement").addEventListener("click", () => {
    collectFromDom();
    state.achievements.push("");
    renderAchievements();
    scheduleSaveAndPreview();
  });

  document.getElementById("add-language").addEventListener("click", () => {
    collectFromDom();
    state.languages.push({ language: "", proficiency: "" });
    renderLanguages();
    scheduleSaveAndPreview();
  });

  async function downloadBlob(path, filename) {
    const res = await apiFetch(path, { method: "GET" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  document.getElementById("btn-pdf").addEventListener("click", async () => {
    try {
      collectFromDom();
      await saveResume();
      const name = (state.personal.full_name || "resume").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "_");
      await downloadBlob("/api/export/pdf", `${name || "resume"}.pdf`);
    } catch (e) {
      showToast(e.message || "PDF export failed", true);
    }
  });

  document.getElementById("btn-docx").addEventListener("click", async () => {
    try {
      collectFromDom();
      await saveResume();
      const name = (state.personal.full_name || "resume").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "_");
      await downloadBlob("/api/export/docx", `${name || "resume"}.docx`);
    } catch (e) {
      showToast(e.message || "DOCX export failed", true);
    }
  });

  document.getElementById("btn-html").addEventListener("click", async () => {
    try {
      collectFromDom();
      await saveResume();
      const res = await apiFetch("/api/export/html", { method: "GET" });
      const html = await res.text();
      const w = window.open("", "_blank");
      if (w) {
        w.document.open();
        w.document.write(html);
        w.document.close();
      }
    } catch (e) {
      showToast(e.message || "Could not open HTML preview", true);
    }
  });

  document.getElementById("btn-ai-summary").addEventListener("click", async () => {
    const btn = document.getElementById("btn-ai-summary");
    collectFromDom();
    btn.disabled = true;
    try {
      const keySkills = state.skills
        .map((c) => c.items.join(", "))
        .join(", ");
      const res = await apiFetch("/api/ai/summary", {
        method: "POST",
        body: JSON.stringify({
          target_role: document.getElementById("ai-target-role").value.trim(),
          years_experience: document.getElementById("ai-years").value.trim(),
          key_skills: keySkills,
          highlights: "",
          current_summary: state.professional_summary || "",
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      state.professional_summary = data.summary || state.professional_summary;
      applyPersonalToDom();
      scheduleSaveAndPreview();
      showToast("Summary updated.");
    } catch (e) {
      showToast(e.message || "AI failed", true);
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById("btn-ai-skills").addEventListener("click", async () => {
    const btn = document.getElementById("btn-ai-skills");
    collectFromDom();
    btn.disabled = true;
    try {
      const existing = state.skills
        .map((c) => `${c.category_name}: ${c.items.join(", ")}`)
        .join(" | ");
      const res = await apiFetch("/api/ai/skills", {
        method: "POST",
        body: JSON.stringify({
          job_role: document.getElementById("ai-skill-role").value.trim(),
          industry: document.getElementById("ai-skill-industry").value.trim(),
          existing_skills: existing,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      const list = String(data.skills || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (!list.length) throw new Error("No skills returned");
      let tech = state.skills.find((c) => /technical/i.test(c.category_name));
      if (!tech) {
        tech = { category_name: "Technical Skills", items: [] };
        state.skills.unshift(tech);
      }
      tech.items = Array.from(new Set([...tech.items, ...list]));
      renderSkills();
      scheduleSaveAndPreview();
      showToast("Skills merged into Technical Skills (create new categories as needed).");
    } catch (e) {
      showToast(e.message || "AI failed", true);
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById("btn-ats-score").addEventListener("click", async () => {
    const btn = document.getElementById("btn-ats-score");
    const reportEl = document.getElementById("ats-report");
    collectFromDom();
    btn.disabled = true;
    try {
      await saveResume();
      const res = await apiFetch("/api/ai/ats-score", {
        method: "POST",
        body: JSON.stringify({
          target_role: document.getElementById("ats-target-role").value.trim(),
          job_description: document.getElementById("ats-job-description").value.trim(),
          resume_data: state,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      renderAtsReport(data);
      reportEl.hidden = false;
      showToast("ATS score generated.");
    } catch (e) {
      showToast(e.message || "ATS scoring failed", true);
    } finally {
      btn.disabled = false;
    }
  });

  function renderAtsReport(data) {
    const reportEl = document.getElementById("ats-report");
    const strengths = (data.strengths || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("");
    const concerns = (data.concerns || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("");
    const suggestions = (data.suggestions || []).map((s) => `<li>${escapeHtml(s)}</li>`).join("");
    const breakdown = (data.breakdown || [])
      .map(
        (b) =>
          `<div class="ats-breakdown-item"><strong>${escapeHtml(b.name)}:</strong> ${b.score}/${b.max} - ${escapeHtml(
            b.detail || ""
          )}</div>`
      )
      .join("");

    reportEl.innerHTML = `
      <div class="ats-score-line">
        <div class="ats-score-value">${Number(data.score || 0)}/100</div>
        <div class="ats-rating">${escapeHtml(data.rating || "Unrated")}</div>
      </div>
      <div>${breakdown}</div>
      <h3 style="margin:10px 0 4px;font-size:0.95rem;">Strengths</h3>
      <ul class="ats-list">${strengths || "<li>No strengths detected yet.</li>"}</ul>
      <h3 style="margin:10px 0 4px;font-size:0.95rem;">Concerns</h3>
      <ul class="ats-list">${concerns || "<li>No major concerns detected.</li>"}</ul>
      <h3 style="margin:10px 0 4px;font-size:0.95rem;">Actionable fixes</h3>
      <ul class="ats-list">${suggestions || "<li>Maintain current quality and tailor keywords to each JD.</li>"}</ul>
      <p class="ats-note">${escapeHtml(data.honesty_note || "")}</p>
    `;
  }

  async function boot() {
    setSaveStatus("Starting…");
    try {
      let res = await fetch("/api/resume", { credentials: "include" });
      if (res.status === 401) {
        await ensureSession();
        res = await fetch("/api/resume", { credentials: "include" });
      } else {
        sessionReady = true;
      }
      if (!res.ok) throw new Error("Could not load resume");
      const env = await res.json();
      state = env.resume || emptyResume();
      applyPersonalToDom();
      renderDynamics();
      await saveResume();
      await refreshPreview();
      setSaveStatus("Ready");
    } catch (e) {
      setSaveStatus("Error");
      showToast(e.message || "Startup failed", true);
    }
  }

  boot();
})();
