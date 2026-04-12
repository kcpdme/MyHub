const apiKeyInput = document.getElementById("apiKey");
const saveKeyBtn = document.getElementById("saveKeyBtn");
const apiKeyStatus = document.getElementById("apiKeyStatus");
const appStatus = document.getElementById("appStatus");

const captureForm = document.getElementById("captureForm");
const taskForm = document.getElementById("taskForm");
const noteForm = document.getElementById("noteForm");
const reminderForm = document.getElementById("reminderForm");

const capturesList = document.getElementById("capturesList");
const tasksList = document.getElementById("tasksList");
const notesList = document.getElementById("notesList");
const remindersList = document.getElementById("remindersList");
const summaryGrid = document.getElementById("summaryGrid");
const reminderTargetInput = document.getElementById("reminderTarget");
const reminderDateInput = document.getElementById("reminderDate");
const reminderTimeInput = document.getElementById("reminderTime");
const reminderTimeHint = document.getElementById("reminderTimeHint");
const reminderPresetButtons = document.querySelectorAll("#reminderQuickTime .preset-btn");
const sectionButtons = document.querySelectorAll(".nav-link[data-section]");
const sectionViews = document.querySelectorAll(".section-view[data-section]");

const defaultReminderTarget = reminderTargetInput?.dataset?.defaultTarget || "";
if (reminderTargetInput && !reminderTargetInput.value && defaultReminderTarget) {
  reminderTargetInput.value = defaultReminderTarget;
}

function setStatus(message, type = "info") {
  if (!appStatus) {
    return;
  }
  appStatus.textContent = message;
  appStatus.classList.remove("success", "error");
  if (type === "success") {
    appStatus.classList.add("success");
  }
  if (type === "error") {
    appStatus.classList.add("error");
  }
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function applyDateTime(date) {
  if (!reminderDateInput || !reminderTimeInput) {
    return;
  }

  reminderDateInput.value = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
  reminderTimeInput.value = `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
  updateTimeHint();
}

function selectedReminderDateTime() {
  const datePart = reminderDateInput?.value;
  const timePart = reminderTimeInput?.value;

  if (!datePart || !timePart) {
    return null;
  }

  const selected = new Date(`${datePart}T${timePart}`);
  if (Number.isNaN(selected.getTime())) {
    return null;
  }
  return selected;
}

function updateTimeHint() {
  const selected = selectedReminderDateTime();
  if (!reminderTimeHint) {
    return;
  }
  reminderTimeHint.textContent = selected
    ? `Will send at ${selected.toLocaleString()}`
    : "Pick valid date and time.";
}

function setDefaultReminderDateTime() {
  const now = new Date();
  const next = new Date(now.getTime() + 15 * 60 * 1000);
  next.setSeconds(0, 0);
  applyDateTime(next);
}

function clearPresetActive() {
  reminderPresetButtons.forEach((button) => button.classList.remove("active"));
}

reminderPresetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const minutes = button.dataset.minutes;
    const preset = button.dataset.preset;
    const now = new Date();
    const selected = new Date(now);

    if (minutes) {
      selected.setMinutes(selected.getMinutes() + Number(minutes), 0, 0);
    } else if (preset === "tomorrow-0900") {
      selected.setDate(selected.getDate() + 1);
      selected.setHours(9, 0, 0, 0);
    }

    clearPresetActive();
    button.classList.add("active");
    applyDateTime(selected);
  });
});

function showSection(sectionName) {
  sectionViews.forEach((view) => {
    view.classList.toggle("is-hidden", view.dataset.section !== sectionName);
  });

  sectionButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.section === sectionName);
  });

  localStorage.setItem("automation_hub_section", sectionName);
}

sectionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showSection(button.dataset.section);
  });
});

showSection(localStorage.getItem("automation_hub_section") || "summary");

if (reminderDateInput && reminderTimeInput) {
  reminderDateInput.addEventListener("input", () => {
    clearPresetActive();
    updateTimeHint();
  });
  reminderTimeInput.addEventListener("input", () => {
    clearPresetActive();
    updateTimeHint();
  });
  setDefaultReminderDateTime();
}

const keyStorage = "automation_hub_api_key";
apiKeyInput.value = localStorage.getItem(keyStorage) || "";
if (apiKeyInput.value) {
  apiKeyStatus.textContent = "API key loaded from this browser.";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function nl2br(value) {
  return escapeHtml(value).replaceAll("\n", "<br>");
}

function setListHtml(listEl, html, emptyMessage) {
  if (!html) {
    listEl.innerHTML = `<li class="muted">${escapeHtml(emptyMessage)}</li>`;
    return;
  }
  listEl.innerHTML = html;
}

saveKeyBtn.addEventListener("click", () => {
  const value = apiKeyInput.value.trim();
  localStorage.setItem(keyStorage, value);
  apiKeyStatus.textContent = value ? "API key saved in browser storage." : "API key cleared.";

  if (!value) {
    setStatus("API key cleared.", "success");
    refreshAll();
    return;
  }

  api("/api/summary/today")
    .then(() => {
      setStatus("API key saved and verified.", "success");
      refreshAll();
    })
    .catch((err) => {
      setStatus(`API key saved, but verification failed: ${err.message}`, "error");
    });
});

function headers() {
  return {
    "Content-Type": "application/json",
    "X-API-Key": apiKeyInput.value.trim(),
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...headers(),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text || response.statusText;
    try {
      const parsed = JSON.parse(text);
      if (parsed?.detail) {
        message = typeof parsed.detail === "string" ? parsed.detail : JSON.stringify(parsed.detail);
      }
    } catch {
      // Keep raw text if error body is not JSON.
    }
    throw new Error(message);
  }

  return response.json();
}

function fmtDate(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

captureForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = captureForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  try {
    const payload = {
      content: document.getElementById("captureContent").value.trim(),
      url: document.getElementById("captureUrl").value.trim(),
    };
    await api("/api/captures", { method: "POST", body: JSON.stringify(payload) });
    captureForm.reset();
    await refreshCaptures();
    await refreshSummary();
    setStatus("Capture saved.", "success");
  } catch (err) {
    setStatus(`Capture failed: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
});

taskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = taskForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  try {
    const rawDate = document.getElementById("taskDueDate").value;
    const due_date = rawDate ? new Date(rawDate + "T23:59:59").toISOString() : null;
    const payload = {
      title: document.getElementById("taskTitle").value.trim(),
      priority: document.getElementById("taskPriority").value,
      due_date: due_date
    };
    await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
    taskForm.reset();
    await refreshTasks();
    await refreshSummary();
    setStatus("Task saved.", "success");
  } catch (err) {
    setStatus(`Task save failed: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
});

let currentTaskFilter = "all";
const taskFilterBtns = document.querySelectorAll("#taskFilters button");
taskFilterBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    taskFilterBtns.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentTaskFilter = btn.dataset.filter;
    refreshTasks();
  });
});

noteForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = noteForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  try {
    const payload = {
      title: document.getElementById("noteTitle").value.trim(),
      content: document.getElementById("noteContent").value.trim(),
    };
    await api("/api/notes", { method: "POST", body: JSON.stringify(payload) });
    noteForm.reset();
    await refreshNotes();
    setStatus("Encrypted note saved.", "success");
  } catch (err) {
    setStatus(`Note save failed: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
});

reminderForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const selected = selectedReminderDateTime();
  if (!selected) {
    setStatus("Please choose a valid reminder date and time.", "error");
    return;
  }

  const submitBtn = reminderForm.querySelector("button[type='submit']");
  submitBtn.disabled = true;
  try {
    const isRecurring = document.getElementById("reminderRecurring").checked;
    const recurrenceMinutesValue = document.getElementById("recurrenceMinutes").value;
    const payload = {
      message: document.getElementById("reminderMessage").value.trim(),
      channel: document.getElementById("reminderChannel").value,
      target: reminderTargetInput.value.trim(),
      remind_at: selected.toISOString(),
      is_recurring: isRecurring,
      recurrence_minutes: isRecurring && recurrenceMinutesValue ? Number(recurrenceMinutesValue) : null,
    };
    await api("/api/reminders", { method: "POST", body: JSON.stringify(payload) });
    reminderForm.reset();
    if (reminderTargetInput && defaultReminderTarget) {
      reminderTargetInput.value = defaultReminderTarget;
    }
    setDefaultReminderDateTime();
    await refreshReminders();
    await refreshSummary();
    setStatus("Reminder scheduled.", "success");
  } catch (err) {
    setStatus(`Reminder scheduling failed: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
  }
});

async function refreshCaptures() {
  const items = await api("/api/captures");
  const html = items
    .map(
      (i) =>
        `<li><div>${escapeHtml(i.content)}</div><div class="muted">${escapeHtml(i.url || "")} ${fmtDate(i.created_at)}</div></li>`,
    )
    .join("");
  setListHtml(capturesList, html, "No captures yet.");
}

async function toggleTaskStatus(taskId, nextStatus) {
  await api(`/api/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ status: nextStatus }),
  });
}

async function refreshTasks() {
  const items = await api("/api/tasks");
  const filtered = currentTaskFilter === "all" ? items : items.filter(i => i.status === currentTaskFilter);
  const html = filtered
    .map(
      (i) =>
        `<li>
          <div style="text-decoration: ${i.status === 'done' ? 'line-through' : 'none'}">${escapeHtml(i.title)}</div>
          <div class="muted">${escapeHtml(i.status)} | ${escapeHtml(i.priority)} ${i.due_date ? ' | Due: ' + fmtDate(i.due_date) : ''}</div>
          <button class="ghost" onclick="toggleTaskStatus(${i.id}, '${i.status === "done" ? "todo" : "done"}')">${i.status === "done" ? "Mark Todo" : "Mark Done"}</button>
        </li>`,
    )
    .join("");
  setListHtml(tasksList, html, "No tasks here.");
}

function sendNow(reminderId) {
  api(`/api/reminders/${reminderId}/send-now`, { method: "POST" })
    .then(() => {
      refreshAll();
      setStatus("Reminder sent now.", "success");
    })
    .catch((err) => setStatus(`Send failed: ${err.message}`, "error"));
}

function deleteNote(noteId) {
  api(`/api/notes/${noteId}`, { method: "DELETE" })
    .then(async () => {
      await refreshNotes();
      setStatus("Note deleted.", "success");
    })
    .catch((err) => setStatus(`Delete failed: ${err.message}`, "error"));
}

async function refreshNotes() {
  const items = await api("/api/notes");
  const html = items
    .map(
      (i) =>
        `<li>
          <div><strong>${escapeHtml(i.title || "Untitled")}</strong></div>
          <div>${nl2br(i.content)}</div>
          <div class="muted">updated ${fmtDate(i.updated_at)}</div>
          <button class="ghost" onclick="deleteNote(${i.id})">Delete</button>
        </li>`,
    )
    .join("");
  setListHtml(notesList, html, "No notes yet.");
}

async function refreshReminders() {
  const items = await api("/api/reminders");
  const html = items
    .map(
      (i) =>
        `<li>
          <div>${escapeHtml(i.message)}</div>
          <div class="muted">${escapeHtml(i.channel)} -> ${escapeHtml(i.target)}</div>
          <div class="muted">at ${fmtDate(i.remind_at)} | status: ${escapeHtml(i.status)}</div>
          <div class="muted">${i.is_recurring ? `recurs every ${i.recurrence_minutes} min` : "one-time"}</div>
          <button onclick="sendNow(${i.id})">Send Now</button>
        </li>`,
    )
    .join("");
  setListHtml(remindersList, html, "No reminders yet.");
}

async function refreshSummary() {
  const s = await api("/api/summary/today");
  summaryGrid.innerHTML = `
    <article class="summary-item"><span>Captures Today</span><strong>${s.captures_today}</strong></article>
    <article class="summary-item"><span>Open Tasks</span><strong>${s.tasks_open}</strong></article>
    <article class="summary-item"><span>Pending Reminders</span><strong>${s.reminders_pending}</strong></article>
    <article class="summary-item"><span>Sent Today</span><strong>${s.reminders_sent_today}</strong></article>
  `;
}

async function refreshAll() {
  try {
    await Promise.all([refreshCaptures(), refreshTasks(), refreshNotes(), refreshReminders(), refreshSummary()]);
  } catch (err) {
    setStatus(`Load failed: ${err.message}`, "error");
    showSection("settings");
  }
}

window.sendNow = sendNow;
window.deleteNote = deleteNote;
window.toggleTaskStatus = (taskId, nextStatus) => {
  toggleTaskStatus(taskId, nextStatus)
    .then(async () => {
      await refreshTasks();
      await refreshSummary();
      setStatus("Task updated.", "success");
    })
    .catch((err) => setStatus(`Task update failed: ${err.message}`, "error"));
};
refreshAll();
