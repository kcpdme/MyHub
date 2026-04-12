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
const presetButtons = document.querySelectorAll(".preset-btn");

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
  presetButtons.forEach((button) => button.classList.remove("active"));
}

presetButtons.forEach((button) => {
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
    throw new Error(text || response.statusText);
  }

  return response.json();
}

function fmtDate(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

captureForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      content: document.getElementById("captureContent").value,
      url: document.getElementById("captureUrl").value,
    };
    await api("/api/captures", { method: "POST", body: JSON.stringify(payload) });
    captureForm.reset();
    await refreshCaptures();
    await refreshSummary();
    setStatus("Capture saved.", "success");
  } catch (err) {
    setStatus(`Capture failed: ${err.message}`, "error");
  }
});

taskForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      title: document.getElementById("taskTitle").value,
      priority: document.getElementById("taskPriority").value,
    };
    await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
    taskForm.reset();
    await refreshTasks();
    await refreshSummary();
    setStatus("Task saved.", "success");
  } catch (err) {
    setStatus(`Task save failed: ${err.message}`, "error");
  }
});

noteForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const payload = {
      title: document.getElementById("noteTitle").value,
      content: document.getElementById("noteContent").value,
    };
    await api("/api/notes", { method: "POST", body: JSON.stringify(payload) });
    noteForm.reset();
    await refreshNotes();
    setStatus("Encrypted note saved.", "success");
  } catch (err) {
    setStatus(`Note save failed: ${err.message}`, "error");
  }
});

reminderForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const selected = selectedReminderDateTime();
  if (!selected) {
    setStatus("Please choose a valid reminder date and time.", "error");
    return;
  }

  try {
    const isRecurring = document.getElementById("reminderRecurring").checked;
    const recurrenceMinutesValue = document.getElementById("recurrenceMinutes").value;
    const payload = {
      message: document.getElementById("reminderMessage").value,
      channel: document.getElementById("reminderChannel").value,
      target: reminderTargetInput.value,
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
  }
});

async function refreshCaptures() {
  const items = await api("/api/captures");
  capturesList.innerHTML = items
    .map(
      (i) =>
        `<li><div>${i.content}</div><div class="muted">${i.url || ""} ${fmtDate(i.created_at)}</div></li>`,
    )
    .join("");
}

async function refreshTasks() {
  const items = await api("/api/tasks");
  tasksList.innerHTML = items
    .map(
      (i) =>
        `<li><div>${i.title}</div><div class="muted">${i.status} | ${i.priority} | ${fmtDate(i.due_date)}</div></li>`,
    )
    .join("");
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
  notesList.innerHTML = items
    .map(
      (i) =>
        `<li>
          <div><strong>${i.title || "Untitled"}</strong></div>
          <div>${i.content}</div>
          <div class="muted">updated ${fmtDate(i.updated_at)}</div>
          <button class="ghost" onclick="deleteNote(${i.id})">Delete</button>
        </li>`,
    )
    .join("");
}

async function refreshReminders() {
  const items = await api("/api/reminders");
  remindersList.innerHTML = items
    .map(
      (i) =>
        `<li>
          <div>${i.message}</div>
          <div class="muted">${i.channel} -> ${i.target}</div>
          <div class="muted">at ${fmtDate(i.remind_at)} | status: ${i.status}</div>
          <div class="muted">${i.is_recurring ? `recurs every ${i.recurrence_minutes} min` : "one-time"}</div>
          <button onclick="sendNow(${i.id})">Send Now</button>
        </li>`,
    )
    .join("");
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
  }
}

window.sendNow = sendNow;
window.deleteNote = deleteNote;
refreshAll();
