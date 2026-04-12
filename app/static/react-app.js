import React, { useEffect, useMemo, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);
const rootEl = document.getElementById("root");
const defaultTarget = rootEl?.dataset?.defaultTelegramTarget || "";
const keyStorage = "automation_hub_api_key";

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function navLabel(id) {
  if (id === "summary") return "Overview";
  if (id === "captures") return "Captures";
  if (id === "inbox") return "Inbox";
  if (id === "tasks") return "Tasks";
  if (id === "notes") return "Notes";
  if (id === "reminders") return "Reminders";
  return "Settings";
}

function sectionSubtitle(id) {
  if (id === "summary") return "Operational health and activity overview.";
  if (id === "captures") return "Capture ideas, links, and context instantly.";
  if (id === "inbox") return "Review and triage Telegram intake quickly.";
  if (id === "tasks") return "Plan and track execution priorities.";
  if (id === "notes") return "Store and manage encrypted private notes.";
  if (id === "reminders") return "Schedule outbound reminders and follow-ups.";
  return "Configure access, API keys, and workspace preferences.";
}

function toIsoLocalDateTime(minutesFromNow = 15) {
  const next = new Date(Date.now() + minutesFromNow * 60000);
  next.setSeconds(0, 0);
  const yyyy = next.getFullYear();
  const mm = String(next.getMonth() + 1).padStart(2, "0");
  const dd = String(next.getDate()).padStart(2, "0");
  const hh = String(next.getHours()).padStart(2, "0");
  const mi = String(next.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

function App() {
  const [section, setSection] = useState(localStorage.getItem("hub_section") || "summary");
  const [density, setDensity] = useState(localStorage.getItem("hub_density") || "comfortable");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apiKey, setApiKey] = useState(localStorage.getItem(keyStorage) || "");
  const [status, setStatus] = useState("");
  const [statusKind, setStatusKind] = useState("info");
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState([]);

  const [captures, setCaptures] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [notes, setNotes] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [inboxItems, setInboxItems] = useState([]);
  const [summary, setSummary] = useState(null);

  const [captureForm, setCaptureForm] = useState({ content: "", url: "" });
  const [taskForm, setTaskForm] = useState({ title: "", priority: "medium", dueDate: "" });
  const [noteForm, setNoteForm] = useState({ title: "", content: "" });
  const [taskFilter, setTaskFilter] = useState("all");
  const [reminderForm, setReminderForm] = useState({
    message: "",
    target: defaultTarget,
    remindAt: toIsoLocalDateTime(15),
    recurring: false,
    recurrenceMinutes: "",
  });

  function addToast(message, kind = "info") {
    const id = Date.now() + Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, kind }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }

  function setAppStatus(message, kind = "info") {
    setStatus(message);
    setStatusKind(kind);
    addToast(message, kind);
  }

  async function api(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();

    const response = await fetch(path, { ...options, headers });
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }

    if (!response.ok) {
      const detail = data?.detail || text || response.statusText;
      if (response.status === 401 && !apiKey.trim()) {
        window.location.href = "/";
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  async function refreshAll() {
    try {
      setBusy(true);
      const [capturesData, tasksData, notesData, remindersData, inboxData, summaryData] = await Promise.all([
        api("/api/captures"),
        api("/api/tasks"),
        api("/api/notes"),
        api("/api/reminders"),
        api("/api/inbox"),
        api("/api/summary/today"),
      ]);
      setCaptures(capturesData || []);
      setTasks(tasksData || []);
      setNotes(notesData || []);
      setReminders(remindersData || []);
      setInboxItems(inboxData || []);
      setSummary(summaryData || null);
    } catch (err) {
      setAppStatus(`Load failed: ${err.message}`, "error");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    localStorage.setItem("hub_section", section);
  }, [section]);

  useEffect(() => {
    localStorage.setItem("hub_density", density);
  }, [density]);

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 880) {
        setSidebarOpen(true);
      }
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape" && sidebarOpen && window.innerWidth <= 900) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [sidebarOpen]);

  function openSection(id) {
    setSection(id);
    if (window.innerWidth <= 880) {
      setSidebarOpen(false);
    }
  }

  function focusSectionInput() {
    const firstField = document.querySelector(".section-panel input, .section-panel textarea, .section-panel select");
    if (firstField) {
      firstField.focus();
    }
  }

  function renderEmptyState(title, hint, actionLabel = "", onAction = focusSectionInput) {
    return html`<li className="empty-state-card">
      <div className="empty-state-title">${title}</div>
      <div className="muted">${hint}</div>
      ${actionLabel
        ? html`<button className="ghost empty-cta" onClick=${onAction}>${actionLabel}</button>`
        : ""}
    </li>`;
  }

  useEffect(() => {
    refreshAll();
  }, []);

  async function submitCapture(e) {
    e.preventDefault();
    try {
      await api("/api/captures", { method: "POST", body: JSON.stringify(captureForm) });
      setCaptureForm({ content: "", url: "" });
      await refreshAll();
      setAppStatus("Capture saved.", "success");
    } catch (err) {
      setAppStatus(`Capture failed: ${err.message}`, "error");
    }
  }

  async function submitTask(e) {
    e.preventDefault();
    try {
      const dueDate = taskForm.dueDate ? `${taskForm.dueDate}T23:59:59` : null;
      await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({ title: taskForm.title, priority: taskForm.priority, due_date: dueDate }),
      });
      setTaskForm({ title: "", priority: "medium", dueDate: "" });
      await refreshAll();
      setAppStatus("Task created.", "success");
    } catch (err) {
      setAppStatus(`Task failed: ${err.message}`, "error");
    }
  }

  async function toggleTask(item) {
    try {
      await api(`/api/tasks/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: item.status === "done" ? "todo" : "done" }),
      });
      await refreshAll();
      setAppStatus("Task updated.", "success");
    } catch (err) {
      setAppStatus(`Task update failed: ${err.message}`, "error");
    }
  }

  async function submitNote(e) {
    e.preventDefault();
    try {
      await api("/api/notes", { method: "POST", body: JSON.stringify(noteForm) });
      setNoteForm({ title: "", content: "" });
      await refreshAll();
      setAppStatus("Encrypted note saved.", "success");
    } catch (err) {
      setAppStatus(`Note failed: ${err.message}`, "error");
    }
  }

  async function deleteNote(id) {
    try {
      await api(`/api/notes/${id}`, { method: "DELETE" });
      await refreshAll();
      setAppStatus("Note deleted.", "success");
    } catch (err) {
      setAppStatus(`Delete failed: ${err.message}`, "error");
    }
  }

  async function submitReminder(e) {
    e.preventDefault();
    try {
      const payload = {
        message: reminderForm.message,
        channel: "telegram",
        target: reminderForm.target,
        remind_at: new Date(reminderForm.remindAt).toISOString(),
        is_recurring: reminderForm.recurring,
        recurrence_minutes: reminderForm.recurring && reminderForm.recurrenceMinutes ? Number(reminderForm.recurrenceMinutes) : null,
      };
      await api("/api/reminders", { method: "POST", body: JSON.stringify(payload) });
      setReminderForm({
        message: "",
        target: defaultTarget,
        remindAt: toIsoLocalDateTime(15),
        recurring: false,
        recurrenceMinutes: "",
      });
      await refreshAll();
      setAppStatus("Reminder scheduled.", "success");
    } catch (err) {
      setAppStatus(`Reminder failed: ${err.message}`, "error");
    }
  }

  async function sendNow(id) {
    try {
      await api(`/api/reminders/${id}/send-now`, { method: "POST" });
      await refreshAll();
      setAppStatus("Reminder sent.", "success");
    } catch (err) {
      setAppStatus(`Send failed: ${err.message}`, "error");
    }
  }

  async function analyzeInbox(id) {
    try {
      setAppStatus("Analyzing item with AI...", "info");
      const resp = await api(`/api/inbox/${id}/analyze`, { method: "POST" });
      await refreshAll();
      setAppStatus(`Item categorized: ${resp.tags}`, "success");
    } catch (err) {
      setAppStatus(`Analysis failed: ${err.message}`, "error");
    }
  }

  async function archiveInbox(id) {
    try {
      await api(`/api/inbox/${id}/archive`, { method: "POST" });
      await refreshAll();
      setAppStatus("Inbox item archived.", "success");
    } catch (err) {
      setAppStatus(`Archive failed: ${err.message}`, "error");
    }
  }

  async function inboxToCapture(id) {
    try {
      await api(`/api/inbox/${id}/to-capture`, { method: "POST" });
      await refreshAll();
      setAppStatus("Inbox item promoted to capture.", "success");
    } catch (err) {
      setAppStatus(`Promote failed: ${err.message}`, "error");
    }
  }

  async function inboxToTask(id) {
    try {
      await api(`/api/inbox/${id}/to-task`, {
        method: "POST",
        body: JSON.stringify({ priority: "medium" }),
      });
      await refreshAll();
      setAppStatus("Inbox item promoted to task.", "success");
    } catch (err) {
      setAppStatus(`Promote failed: ${err.message}`, "error");
    }
  }

  function itemCanPreview(item) {
    return Boolean(item?.file_id && ["photo", "sticker", "animation"].includes(item.item_type));
  }

  async function logout() {
    await fetch("/auth/logout", { method: "POST" });
    window.location.href = "/";
  }

  const filteredTasks = useMemo(
    () => (taskFilter === "all" ? tasks : tasks.filter((t) => t.status === taskFilter)),
    [tasks, taskFilter],
  );

  const navItems = ["summary", "captures", "inbox", "tasks", "notes", "reminders", "settings"];

  return html`
    <main className=${`app-shell density-${density}`}>
      <div className="toast-container">
        ${toasts.map(t => html`<div key=${t.id} className=${`toast ${t.kind}`}>${t.message}</div>`)}
      </div>
      <div className="dashboard-layout">
        ${sidebarOpen && window.innerWidth <= 900 ? html`<button className="sidebar-backdrop" onClick=${() => setSidebarOpen(false)} aria-label="Close menu"></button>` : ""}
        <aside id="main-sidebar" className=${`panel sidebar ${sidebarOpen ? "open" : ""}`} aria-hidden=${window.innerWidth <= 900 ? !sidebarOpen : false}>
          <div className="workspace-badge">Operations Console</div>
          <div className="brand">Personal Automation Hub</div>
          <div className="muted">Unified command workspace</div>
          <nav className="sidebar-nav">
            ${navItems.map(
              (id) =>
                html`<button className=${`nav-link ${section === id ? "active" : ""}`} onClick=${() => openSection(id)}>${navLabel(id)}</button>`,
            )}
          </nav>
        </aside>

        <section className="main-content">
          <header className="panel topbar">
            <div className="topbar-left">
              <button className="menu-toggle" onClick=${() => setSidebarOpen((v) => !v)} aria-controls="main-sidebar" aria-expanded=${sidebarOpen}>Menu</button>
              <h1>Command Center</h1>
              <div className="topbar-meta">
                <span className="module-pill">${navLabel(section)}</span>
                <span className="muted">${new Date().toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</span>
              </div>
              <div className="muted">${sectionSubtitle(section)}</div>
            </div>
            <div className="topbar-right">
              <button className="ghost density-toggle" onClick=${() => setDensity((v) => (v === "comfortable" ? "compact" : "comfortable"))}>
                ${density === "comfortable" ? "Compact" : "Comfortable"}
              </button>
              <button className="ghost refresh-btn" onClick=${refreshAll} disabled=${busy}>Refresh</button>
              <div className=${`status-pill ${statusKind}`}>${busy ? "Syncing..." : status || "Ready"}</div>
            </div>
          </header>

          ${section === "summary" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Today Summary</h2>
              <p className="muted">Snapshot of current operations and delivery health.</p>
            </div>
            <div className="summary-grid">
              <article className="summary-item"><span>Captures</span><strong>${summary?.captures_today ?? 0}</strong></article>
              <article className="summary-item"><span>Open Tasks</span><strong>${summary?.tasks_open ?? 0}</strong></article>
              <article className="summary-item"><span>Pending Reminders</span><strong>${summary?.reminders_pending ?? 0}</strong></article>
              <article className="summary-item"><span>Sent Today</span><strong>${summary?.reminders_sent_today ?? 0}</strong></article>
            </div>
          </section>`}

          ${section === "captures" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Quick Capture</h2>
              <p className="muted">Save context immediately before it gets lost.</p>
            </div>
            <form onSubmit=${submitCapture} className="stack">
              <textarea required value=${captureForm.content} onInput=${(e) => setCaptureForm({ ...captureForm, content: e.target.value })} placeholder="Idea, thought, link context" />
              <input type="url" value=${captureForm.url} onInput=${(e) => setCaptureForm({ ...captureForm, url: e.target.value })} placeholder="Optional URL" />
              <button disabled=${busy}>Save Capture</button>
            </form>
            <ul className="list">
              ${captures.map((i) => html`<li><div>${i.content}</div><div className="muted">${i.url || ""} ${formatDate(i.created_at)}</div></li>`)}
              ${captures.length === 0 && renderEmptyState("No captures yet", "Use the form above to save your first idea.", "Focus Capture Form")}
            </ul>
          </section>`}

          ${section === "inbox" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Telegram Inbox</h2>
              <p className="muted">Anything you share to your Telegram bot lands here automatically.</p>
            </div>
            <ul className="inbox-grid">
              ${busy && inboxItems.length === 0 ? 
                [1,2,3].map(() => html`<li>
                  <div className="skeleton" style=${{width: '40%'}}></div>
                  <div className="skeleton thumb"></div>
                  <div className="skeleton"></div>
                  <div className="skeleton" style=${{width: '70%'}}></div>
                </li>`) 
                :
                inboxItems.map((item) => html`<li>
                  <div className="inbox-headline">
                    <strong>${item.item_type.toUpperCase()}</strong>
                    <div className="inbox-meta">
                      <span className="muted">#${item.id}</span>
                      <button className="ghost chip-btn" onClick=${() => analyzeInbox(item.id)}>Auto-Tag</button>
                    </div>
                  </div>
                  ${itemCanPreview(item)
                    ? html`<img className="inbox-thumb" src=${`/api/inbox/${item.id}/media`} alt="Inbox media" loading="lazy" />`
                    : ""}
                  <div className="inbox-body">${item.text || "(no text)"}</div>
                  <div className="muted">${formatDate(item.created_at)} | msg #${item.message_id}</div>
                  <div className="row inbox-actions">
                    <button className="ghost" onClick=${() => inboxToCapture(item.id)}>To Capture</button>
                    <button className="ghost" onClick=${() => inboxToTask(item.id)}>To Task</button>
                    <button className="ghost" onClick=${() => archiveInbox(item.id)}>Archive</button>
                  </div>
                </li>`)
              }
              ${!busy && inboxItems.length === 0 && renderEmptyState("Inbox is empty", "Send text, photos, or files to your bot.", "Refresh", refreshAll)}
            </ul>
          </section>`}

          ${section === "tasks" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Tasks</h2>
              <p className="muted">Prioritize work and update completion status.</p>
            </div>
            <form onSubmit=${submitTask} className="stack">
              <input required value=${taskForm.title} onInput=${(e) => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="Task title" />
              <div className="row">
                <select value=${taskForm.priority} onChange=${(e) => setTaskForm({ ...taskForm, priority: e.target.value })}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <input type="date" value=${taskForm.dueDate} onInput=${(e) => setTaskForm({ ...taskForm, dueDate: e.target.value })} />
              </div>
              <button disabled=${busy}>Add Task</button>
            </form>
            <div className="filter-row">
              ${["all", "todo", "done"].map(
                (f) => html`<button className=${`ghost ${taskFilter === f ? "active" : ""}`} onClick=${() => setTaskFilter(f)}>${f}</button>`,
              )}
            </div>
            <ul className="list">
              ${filteredTasks.map(
                (t) => html`<li>
                  <div className=${t.status === "done" ? "done" : ""}>${t.title}</div>
                  <div className="muted">${t.status} | ${t.priority} | ${formatDate(t.due_date)}</div>
                  <button className="ghost" onClick=${() => toggleTask(t)}>${t.status === "done" ? "Mark Todo" : "Mark Done"}</button>
                </li>`,
              )}
              ${filteredTasks.length === 0 && renderEmptyState("No tasks in this filter", "Add a task above and track progress.", "Focus Task Form")}
            </ul>
          </section>`}

          ${section === "notes" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Encrypted Notes</h2>
              <p className="muted">Keep sensitive notes protected and searchable.</p>
            </div>
            <form onSubmit=${submitNote} className="stack">
              <input value=${noteForm.title} onInput=${(e) => setNoteForm({ ...noteForm, title: e.target.value })} placeholder="Title" />
              <textarea required value=${noteForm.content} onInput=${(e) => setNoteForm({ ...noteForm, content: e.target.value })} placeholder="Private note" />
              <button disabled=${busy}>Save Note</button>
            </form>
            <ul className="list">
              ${notes.map(
                (n) => html`<li>
                  <div><strong>${n.title || "Untitled"}</strong></div>
                  <div>${n.content}</div>
                  <div className="muted">Updated ${formatDate(n.updated_at)}</div>
                  <button className="ghost" onClick=${() => deleteNote(n.id)}>Delete</button>
                </li>`,
              )}
              ${notes.length === 0 && renderEmptyState("No notes yet", "Create your first encrypted note above.", "Focus Note Form")}
            </ul>
          </section>`}

          ${section === "reminders" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Reminders</h2>
              <p className="muted">Schedule message delivery with optional recurrence.</p>
            </div>
            <form onSubmit=${submitReminder} className="stack">
              <input required value=${reminderForm.message} onInput=${(e) => setReminderForm({ ...reminderForm, message: e.target.value })} placeholder="Reminder message" />
              <input required value=${reminderForm.target} onInput=${(e) => setReminderForm({ ...reminderForm, target: e.target.value })} placeholder="Telegram chat id" />
              <input type="datetime-local" required value=${reminderForm.remindAt} onInput=${(e) => setReminderForm({ ...reminderForm, remindAt: e.target.value })} />
              <div className="quick-row">
                <button className="ghost" onClick=${(e) => { e.preventDefault(); setReminderForm({ ...reminderForm, remindAt: toIsoLocalDateTime(15) }); }}>+15m</button>
                <button className="ghost" onClick=${(e) => { e.preventDefault(); setReminderForm({ ...reminderForm, remindAt: toIsoLocalDateTime(30) }); }}>+30m</button>
                <button className="ghost" onClick=${(e) => { e.preventDefault(); setReminderForm({ ...reminderForm, remindAt: toIsoLocalDateTime(60) }); }}>+1h</button>
              </div>
              <label className="inline-check">
                <input type="checkbox" checked=${reminderForm.recurring} onChange=${(e) => setReminderForm({ ...reminderForm, recurring: e.target.checked })} />
                Repeat reminder
              </label>
              ${reminderForm.recurring && html`<input type="number" min="1" placeholder="Recurrence minutes" value=${reminderForm.recurrenceMinutes} onInput=${(e) => setReminderForm({ ...reminderForm, recurrenceMinutes: e.target.value })} />`}
              <button disabled=${busy}>Schedule Reminder</button>
            </form>
            <ul className="list">
              ${reminders.map(
                (r) => html`<li>
                  <div>${r.message}</div>
                  <div className="muted">${r.channel} -> ${r.target}</div>
                  <div className="muted">${formatDate(r.remind_at)} | ${r.status}</div>
                  <button onClick=${() => sendNow(r.id)}>Send Now</button>
                </li>`,
              )}
              ${reminders.length === 0 && renderEmptyState("No reminders yet", "Schedule a reminder using the form above.", "Focus Reminder Form")}
            </ul>
          </section>`}

          ${section === "settings" &&
          html`<section className="panel section-panel">
            <div className="section-head">
              <h2>Settings</h2>
              <p className="muted">Telegram session auth is enabled. API key is optional for external API clients.</p>
            </div>
            <div className="stack">
              <input type="password" placeholder="Optional X-API-Key" value=${apiKey} onInput=${(e) => setApiKey(e.target.value)} />
              <button
                className="ghost"
                onClick=${() => {
                  localStorage.setItem(keyStorage, apiKey.trim());
                  setAppStatus(apiKey.trim() ? "API key saved." : "API key cleared.", "success");
                }}
              >
                Save API Key
              </button>
              <button className="ghost" onClick=${logout}>Logout</button>
            </div>
          </section>`}
        </section>
      </div>
    </main>
  `;
}

createRoot(rootEl).render(html`<${App} />`);
