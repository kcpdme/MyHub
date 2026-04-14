import React, { useEffect, useMemo, useState, useCallback, useRef } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";

const html = htm.bind(React.createElement);
const rootEl = document.getElementById("root");
const defaultTarget = rootEl?.dataset?.defaultTelegramTarget || "";
const keyStorage = "automation_hub_api_key";

// ─── Mini App mode detection ───────────────────────────────────────────────
// When served via /miniapp the <div id="root"> has data-miniapp-mode="true".
// In this mode the API key comes from sessionStorage (set by miniapp auth).
const isMiniApp = rootEl?.dataset?.miniappMode === "true";
const tgWebApp = window.Telegram?.WebApp || null;
const miniAppUser = (() => {
  try { return JSON.parse(sessionStorage.getItem("miniapp_user") || "{}"); }
  catch { return {}; }
})();


/* ─── SVG Icon components (inline Lucide-style) ─── */
function Icon({ name, size = 18 }) {
  const s = size;
  const icons = {
    zap: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>`,
    "layout-dashboard": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>`,
    "pen-line": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z"/></svg>`,
    inbox: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`,
    "check-square": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/></svg>`,
    "file-lock": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><rect width="8" height="6" x="8" y="12" rx="1"/><path d="M10 12v-2a2 2 0 1 1 4 0v2"/></svg>`,
    bell: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`,
    settings: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
    search: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
    plus: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>`,
    trash: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>`,
    check: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>`,
    undo: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg>`,
    send: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>`,
    archive: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/></svg>`,
    "arrow-up-right": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>`,
    "refresh-cw": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/></svg>`,
    "log-out": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>`,
    keyboard: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="M6 8h.001"/><path d="M10 8h.001"/><path d="M14 8h.001"/><path d="M18 8h.001"/><path d="M8 12h.001"/><path d="M12 12h.001"/><path d="M16 12h.001"/><path d="M7 16h10"/></svg>`,
    menu: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>`,
    "bar-chart": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/></svg>`,
    tag: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/></svg>`,
    link: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
    clock: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`,
    repeat: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>`,
    key: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4"/><path d="m21 2-9.6 9.6"/><circle cx="7.5" cy="15.5" r="5.5"/></svg>`,
    save: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/></svg>`,
    copy: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`,
    edit: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
    x: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`,
    "alert-triangle": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`,
    activity: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
    "archive-x": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="m9.5 17 5-5"/><path d="m9.5 12 5 5"/></svg>`,
    timer: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/></svg>`,
    flame: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`,
    download: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>`,
    moon: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`,
    sun: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`,
    play: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="6 3 20 12 6 21 6 3"/></svg>`,
    pause: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="4" height="16" x="6" y="4"/><rect width="4" height="16" x="14" y="4"/></svg>`,
    "skip-forward": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" x2="19" y1="5" y2="19"/></svg>`,
    "loader": html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v4"/><path d="m16.2 7.8 2.9-2.9"/><path d="M18 12h4"/><path d="m16.2 16.2 2.9 2.9"/><path d="M12 18v4"/><path d="m4.9 19.1 2.9-2.9"/><path d="M2 12h4"/><path d="m4.9 4.9 2.9 2.9"/></svg>`,
    target: html`<svg width=${s} height=${s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
  };
  return icons[name] || null;
}

/* ─── Helpers ─── */
function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function formatDateShort(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    month: "short", day: "numeric",
  });
}

function relativeTime(value) {
  if (!value) return "";
  const diff = new Date(value) - Date.now();
  const absDiff = Math.abs(diff);
  const mins = Math.floor(absDiff / 60000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (diff > 0) {
    if (mins < 60) return `in ${mins}m`;
    if (hours < 24) return `in ${hours}h ${mins % 60}m`;
    return `in ${days}d`;
  }
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
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

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

const NAV_CONFIG = [
  { id: "summary",  label: "Overview",  icon: "layout-dashboard" },
  { id: "captures", label: "Captures",  icon: "pen-line" },
  { id: "inbox",    label: "Inbox",     icon: "inbox" },
  { id: "tasks",    label: "Tasks",     icon: "check-square" },
  { id: "notes",    label: "Notes",     icon: "file-lock" },
];

/* Secondary nav (shown as icon-buttons in the topbar) */
const TOPBAR_EXTRA = [
  { id: "habits",   label: "Habits",       icon: "target" },
  { id: "pomodoro", label: "Focus Timer",   icon: "timer" },
  { id: "settings", label: "Settings",      icon: "settings" },
];

const SECTION_META = {
  summary:  { title: "Overview",       subtitle: "Activity snapshot and operational health at a glance." },
  captures: { title: "Quick Capture",  subtitle: "Save ideas, links, and context before they're lost." },
  inbox:    { title: "Telegram Inbox", subtitle: "Review and triage incoming items from your bot." },
  tasks:    { title: "Tasks",          subtitle: "Track priorities, execution progress and reminders." },
  notes:    { title: "Encrypted Notes",subtitle: "Secure, encrypted notes stored at rest." },
  habits:   { title: "Habit Tracker",  subtitle: "Build consistent habits with daily tracking and streaks." },
  pomodoro: { title: "Focus Timer",    subtitle: "Pomodoro technique — work in focused intervals." },
  settings: { title: "Settings",       subtitle: "Configure keys, preferences, and workspace." },
};

/* ─── Confirm Dialog Component ─── */
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return html`
    <div className="confirm-overlay" onClick=${onCancel}>
      <div className="confirm-modal" onClick=${(e) => e.stopPropagation()}>
        <div className="confirm-icon">
          <${Icon} name="alert-triangle" size=${24} />
        </div>
        <div className="confirm-content">
          <h3>Confirm Action</h3>
          <p>${message}</p>
        </div>
        <div className="confirm-actions">
          <button className="ghost" onClick=${onCancel}> Cancel</button>
          <button className="danger-ghost" onClick=${onConfirm}>
            <${Icon} name="trash" size=${14} /> Delete
          </button>
        </div>
      </div>
    </div>
  `;
}

/* ─── Edit Modal Component ─── */
function EditModal({ title, fields, values, onSave, onCancel }) {
  const [formValues, setFormValues] = useState({ ...values });

  return html`
    <div className="confirm-overlay" onClick=${onCancel}>
      <div className="edit-modal" onClick=${(e) => e.stopPropagation()}>
        <div className="edit-modal-header">
          <h3><${Icon} name="edit" size=${16} /> ${title}</h3>
          <button className="btn-icon ghost" onClick=${onCancel}><${Icon} name="x" size=${16} /></button>
        </div>
        <div className="edit-modal-body">
          ${fields.map(f => html`
            <div key=${f.key} style=${{ marginBottom: "0.65rem" }}>
              <label className="field-label">${f.label}</label>
              ${f.type === "textarea"
                ? html`<textarea
                    value=${formValues[f.key] || ""}
                    onInput=${(e) => setFormValues({ ...formValues, [f.key]: e.target.value })}
                    rows="4"
                    placeholder=${f.placeholder || ""}
                  />`
                : f.type === "select"
                ? html`<select value=${formValues[f.key] || ""} onChange=${(e) => setFormValues({ ...formValues, [f.key]: e.target.value })}>
                    ${(f.options || []).map(o => html`<option key=${o.value} value=${o.value}>${o.label}</option>`)}
                  </select>`
                : html`<input
                    type=${f.type || "text"}
                    value=${formValues[f.key] || ""}
                    onInput=${(e) => setFormValues({ ...formValues, [f.key]: e.target.value })}
                    placeholder=${f.placeholder || ""}
                  />`
              }
            </div>
          `)}
        </div>
        <div className="confirm-actions">
          <button className="ghost" onClick=${onCancel}>Cancel</button>
          <button onClick=${() => onSave(formValues)}>
            <${Icon} name="save" size=${14} /> Save Changes
          </button>
        </div>
      </div>
    </div>
  `;
}

function InboxPreviewModal({ item, onClose }) {
  const canPreviewImage = Boolean(item?.file_id && ["photo", "sticker", "animation"].includes(item.item_type));
  const canOpenFile = Boolean(item?.file_id || item?.item_type === "text");

  return html`
    <div className="confirm-overlay" onClick=${onClose}>
      <div className="edit-modal inbox-preview-modal" onClick=${(e) => e.stopPropagation()}>
        <div className="edit-modal-header">
          <h3><${Icon} name="inbox" size=${16} /> Inbox #${item.id}</h3>
          <button className="btn-icon ghost" onClick=${onClose}><${Icon} name="x" size=${16} /></button>
        </div>
        <div className="edit-modal-body">
          <div className="list-item-meta" style=${{ marginBottom: "0.65rem" }}>
            <span className="status-badge note">${item.item_type}</span>
            <span><${Icon} name="clock" size=${12} /> ${formatDate(item.created_at)}</span>
            <span>msg #${item.message_id}</span>
          </div>
          ${canPreviewImage ? html`
            <img className="inbox-thumb" src=${`/api/inbox/${item.id}/media`} alt="Inbox media" />
          ` : ""}
          <div className="inbox-preview-text">${item.text || "(no text content)"}</div>
        </div>
        <div className="confirm-actions">
          ${canOpenFile ? html`
            <button className="ghost" onClick=${() => window.open(`/api/inbox/${item.id}/media`, "_blank", "noopener,noreferrer")}>
              <${Icon} name="download" size=${14} /> Open File
            </button>
          ` : ""}
          <button className="ghost" onClick=${onClose}>Close</button>
        </div>
      </div>
    </div>
  `;
}

/* ─── Progress Bar Component ─── */
function ProgressBar({ value, max, label, color = "var(--green-500)" }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return html`
    <div className="progress-wrapper">
      <div className="progress-header">
        <span className="progress-label">${label}</span>
        <span className="progress-value">${value}${max > 0 ? ` / ${max}` : ""}</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style=${{ width: `${pct}%`, background: color }}></div>
      </div>
    </div>
  `;
}

/* ─── Pomodoro Timer Component ─── */
function PomodoroTimer({ addToast }) {
  const MODES = { focus: 25 * 60, short: 5 * 60, long: 15 * 60 };
  const [mode, setMode] = useState("focus");
  const [seconds, setSeconds] = useState(MODES.focus);
  const [running, setRunning] = useState(false);
  const [sessions, setSessions] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setSeconds(s => {
          if (s <= 1) {
            clearInterval(intervalRef.current);
            setRunning(false);
            // Play notification sound
            try { new Audio("data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbX19fYGFhYWFhX19fX19gYWFhYWFfX19fX2BhYWFhYV9fX19fYGFhQ==").play(); } catch {}
            if (mode === "focus") {
              setSessions(s => s + 1);
              addToast("Focus session complete! Take a break.", "success");
            } else {
              addToast("Break over! Time to focus.", "info");
            }
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    }
    return () => clearInterval(intervalRef.current);
  }, [running]);

  function switchMode(m) {
    setRunning(false);
    clearInterval(intervalRef.current);
    setMode(m);
    setSeconds(MODES[m]);
  }

  function toggle() { setRunning(r => !r); }
  function reset() { setRunning(false); clearInterval(intervalRef.current); setSeconds(MODES[mode]); }

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");
  const pct = ((MODES[mode] - seconds) / MODES[mode]) * 100;

  return html`
    <section className="panel section-panel" id="section-pomodoro">
      <div className="section-head">
        <h2><${Icon} name="timer" /> Focus Timer</h2>
        <p className="muted">Pomodoro technique — work in focused intervals for better productivity.</p>
      </div>

      <div className="pomodoro-container">
        <div className="pomodoro-mode-selector">
          ${[["focus", "Focus", "25m"], ["short", "Short Break", "5m"], ["long", "Long Break", "15m"]].map(([m, label, time]) => html`
            <button key=${m} className=${`ghost sm ${mode === m ? "active" : ""}`} onClick=${() => switchMode(m)}>
              ${label} (${time})
            </button>
          `)}
        </div>

        <div className="pomodoro-timer">
          <svg className="pomodoro-ring" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" strokeWidth="6" fill="none" stroke="var(--line)" />
            <circle cx="60" cy="60" r="52" strokeWidth="6" fill="none"
              stroke=${mode === "focus" ? "var(--green-500)" : "var(--blue-600)"}
              strokeDasharray=${2 * Math.PI * 52}
              strokeDashoffset=${2 * Math.PI * 52 * (1 - pct / 100)}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
              style=${{ transition: "stroke-dashoffset 0.3s ease" }}
            />
          </svg>
          <div className="pomodoro-display">
            <div className="pomodoro-time">${mm}:${ss}</div>
            <div className="pomodoro-mode-label">${mode === "focus" ? "Focus" : mode === "short" ? "Short Break" : "Long Break"}</div>
          </div>
        </div>

        <div className="pomodoro-controls">
          <button className=${running ? "ghost" : ""} onClick=${toggle}>
            <${Icon} name=${running ? "pause" : "play"} size=${16} /> ${running ? "Pause" : "Start"}
          </button>
          <button className="ghost" onClick=${reset}>
            <${Icon} name="refresh-cw" size=${14} /> Reset
          </button>
        </div>

        <div className="pomodoro-stats">
          <div className="pomodoro-stat">
            <${Icon} name="flame" size=${16} />
            <span>${sessions} session${sessions !== 1 ? "s" : ""} today</span>
          </div>
        </div>
      </div>
    </section>
  `;
}


/* ─── Main App ─── */
function App() {
  const [section, setSection] = useState(localStorage.getItem("hub_section") || "summary");
  const [density, setDensity] = useState(localStorage.getItem("hub_density") || "comfortable");
  const [inboxView, setInboxView] = useState(localStorage.getItem("hub_inbox_view") || "list");
  const [darkMode, setDarkMode] = useState(isMiniApp ? true : localStorage.getItem("hub_dark_mode") === "true");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [taskSubTab, setTaskSubTab] = useState("tasks"); // "tasks" | "reminders"
  // Mini App mode: read API key from sessionStorage (set by miniapp.html auth handshake).
  const [apiKey, setApiKey] = useState(
    isMiniApp
      ? sessionStorage.getItem(keyStorage) || ""
      : localStorage.getItem(keyStorage) || ""
  );
  const [status, setStatus] = useState("");
  const [statusKind, setStatusKind] = useState("info");
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(localStorage.getItem("hub_auto_refresh") !== "false");

  const [captures, setCaptures] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [notes, setNotes] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [inboxItems, setInboxItems] = useState([]);
  const [summary, setSummary] = useState(null);
  const [habits, setHabits] = useState([]);

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
  const [habitForm, setHabitForm] = useState({ name: "" });

  /* ─── Confirm / Edit Dialog State ─── */
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [editDialog, setEditDialog] = useState(null);
  const [inboxPreview, setInboxPreview] = useState(null);

  const searchRef = useRef(null);

  /* ─── Dark Mode Toggle ─── */
  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
    localStorage.setItem("hub_dark_mode", darkMode);
  }, [darkMode]);

  /* ─── Toast System ─── */
  const addToast = useCallback((message, kind = "info") => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, kind }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  function setAppStatus(message, kind = "info") {
    setStatus(message);
    setStatusKind(kind);
    addToast(message, kind);
  }

  /* ─── Confirm Helper ─── */
  function confirmAction(message, action) {
    setConfirmDialog({ message, action });
  }

  /* ─── API Helper ─── */
  async function api(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
    // Include CSRF token for session-authenticated browser requests (non-Mini App).
    if (!isMiniApp) {
      const csrfToken = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1];
      if (csrfToken && !apiKey.trim()) headers["X-CSRF-Token"] = csrfToken;
    }
    const response = await fetch(path, { ...options, headers });
    const text = await response.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = null; }
    if (!response.ok) {
      const detail = data?.detail || text || response.statusText;
      if (response.status === 401 && !isMiniApp) {
        window.location.href = "/";
        return;
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  /* ─── Unwrap paginated response ─── */
  function unwrap(resp) {
    if (!resp) return [];
    // Paginated responses have an .items array; flat arrays returned as-is.
    if (Array.isArray(resp)) return resp;
    if (Array.isArray(resp.items)) return resp.items;
    return [];
  }

  /* ─── Data Refresh ─── */
  async function refreshAll() {
    try {
      setBusy(true);
      // Fetch all pages up to 200 items per list for local filtering.
      const [cap, tsk, nts, rem, ibx, sum, hab] = await Promise.all([
        api("/api/captures?page_size=200"),
        api("/api/tasks?page_size=200"),
        api("/api/notes?page_size=200"),
        api("/api/reminders?page_size=200"),
        api("/api/inbox?page_size=200"),
        api("/api/summary/today"),
        api("/api/habits"),
      ]);
      setCaptures(unwrap(cap));
      setTasks(unwrap(tsk));
      setNotes(unwrap(nts));
      setReminders(unwrap(rem));
      setInboxItems(unwrap(ibx));
      setSummary(sum || null);
      setHabits(Array.isArray(hab) ? hab : unwrap(hab));
    } catch (err) {
      setAppStatus(`Load failed: ${err.message}`, "error");
    } finally {
      setBusy(false);
    }
  }

  /* ─── Effects ─── */
  useEffect(() => { localStorage.setItem("hub_section", section); }, [section]);
  useEffect(() => { localStorage.setItem("hub_density", density); }, [density]);
  useEffect(() => { localStorage.setItem("hub_inbox_view", inboxView); }, [inboxView]);
  useEffect(() => { localStorage.setItem("hub_auto_refresh", autoRefresh); }, [autoRefresh]);
  useEffect(() => { refreshAll(); }, []);

  /* ─── Auto-refresh every 60 seconds ─── */
  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => { refreshAll(); }, 60000);
    return () => clearInterval(timer);
  }, [autoRefresh]);

  useEffect(() => {
    const onResize = () => { if (window.innerWidth > 900) setSidebarOpen(true); };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  /* ─── Keyboard Shortcuts ─── */
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;
      if (e.key === "Escape") {
        if (confirmDialog) { setConfirmDialog(null); return; }
        if (editDialog) { setEditDialog(null); return; }
        if (showShortcuts) { setShowShortcuts(false); return; }
        if (sidebarOpen && window.innerWidth <= 900) { setSidebarOpen(false); return; }
      }
      if (e.key === "?") { setShowShortcuts((v) => !v); return; }
      if (e.key === "/") { e.preventDefault(); searchRef.current?.focus(); return; }
      if (e.key === "r" && !e.ctrlKey && !e.metaKey) { refreshAll(); return; }
      if (e.key === "d" && !e.ctrlKey && !e.metaKey) { setDarkMode(v => !v); return; }
      const navKeys = { "1": "summary", "2": "captures", "3": "inbox", "4": "tasks", "5": "notes", "6": "reminders", "7": "habits", "8": "pomodoro", "9": "settings" };
      if (navKeys[e.key]) { openSection(navKeys[e.key]); return; }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [showShortcuts, sidebarOpen, confirmDialog, editDialog]);

  /* ─── Navigation ─── */
  function openSection(id) {
    setSection(id);
    setSearchQuery("");
    if (window.innerWidth <= 900) setSidebarOpen(false);
  }

  /* ─── CRUD: Captures ─── */
  async function submitCapture(e) {
    e.preventDefault();
    try {
      await api("/api/captures", { method: "POST", body: JSON.stringify(captureForm) });
      setCaptureForm({ content: "", url: "" });
      await refreshAll();
      setAppStatus("Capture saved.", "success");
    } catch (err) { setAppStatus(`Capture failed: ${err.message}`, "error"); }
  }

  async function deleteCapture(id) {
    confirmAction("Delete this capture permanently?", async () => {
      try {
        await api(`/api/captures/${id}`, { method: "DELETE" });
        await refreshAll();
        setAppStatus("Capture deleted.", "success");
      } catch (err) { setAppStatus(`Delete failed: ${err.message}`, "error"); }
    });
  }

  function editCapture(c) {
    setEditDialog({
      title: "Edit Capture",
      fields: [
        { key: "content", label: "Content", type: "textarea", placeholder: "Capture content…" },
        { key: "url", label: "URL", type: "url", placeholder: "Optional URL reference" },
      ],
      values: { content: c.content, url: c.url || "" },
      onSave: async (vals) => {
        try {
          await api(`/api/captures/${c.id}`, { method: "PATCH", body: JSON.stringify(vals) });
          setEditDialog(null);
          await refreshAll();
          setAppStatus("Capture updated.", "success");
        } catch (err) { setAppStatus(`Update failed: ${err.message}`, "error"); }
      },
    });
  }

  /* ─── CRUD: Tasks ─── */
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
    } catch (err) { setAppStatus(`Task failed: ${err.message}`, "error"); }
  }

  async function toggleTask(item) {
    try {
      const nextStatus = item.status === "done" ? "todo" : item.status === "todo" ? "in_progress" : "done";
      await api(`/api/tasks/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      await refreshAll();
      setAppStatus("Task updated.", "success");
    } catch (err) { setAppStatus(`Update failed: ${err.message}`, "error"); }
  }

  async function setTaskStatus(item, status) {
    try {
      await api(`/api/tasks/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await refreshAll();
      setAppStatus("Task updated.", "success");
    } catch (err) { setAppStatus(`Update failed: ${err.message}`, "error"); }
  }

  async function deleteTask(id) {
    confirmAction("Delete this task permanently?", async () => {
      try {
        await api(`/api/tasks/${id}`, { method: "DELETE" });
        await refreshAll();
        setAppStatus("Task deleted.", "success");
      } catch (err) { setAppStatus(`Delete failed: ${err.message}`, "error"); }
    });
  }

  function editTask(t) {
    setEditDialog({
      title: "Edit Task",
      fields: [
        { key: "title", label: "Title", type: "text", placeholder: "Task title" },
        { key: "priority", label: "Priority", type: "select", options: [
          { value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" }
        ]},
      ],
      values: { title: t.title, priority: t.priority },
      onSave: async (vals) => {
        try {
          await api(`/api/tasks/${t.id}`, { method: "PATCH", body: JSON.stringify(vals) });
          setEditDialog(null);
          await refreshAll();
          setAppStatus("Task updated.", "success");
        } catch (err) { setAppStatus(`Update failed: ${err.message}`, "error"); }
      },
    });
  }

  /* ─── CRUD: Notes ─── */
  async function submitNote(e) {
    e.preventDefault();
    try {
      await api("/api/notes", { method: "POST", body: JSON.stringify(noteForm) });
      setNoteForm({ title: "", content: "" });
      await refreshAll();
      setAppStatus("Encrypted note saved.", "success");
    } catch (err) { setAppStatus(`Note failed: ${err.message}`, "error"); }
  }

  async function deleteNote(id) {
    confirmAction("Delete this encrypted note permanently?", async () => {
      try {
        await api(`/api/notes/${id}`, { method: "DELETE" });
        await refreshAll();
        setAppStatus("Note deleted.", "success");
      } catch (err) { setAppStatus(`Delete failed: ${err.message}`, "error"); }
    });
  }

  function editNote(n) {
    setEditDialog({
      title: "Edit Note",
      fields: [
        { key: "title", label: "Title", type: "text", placeholder: "Note title (optional)" },
        { key: "content", label: "Content", type: "textarea", placeholder: "Note content…" },
      ],
      values: { title: n.title || "", content: n.content || "" },
      onSave: async (vals) => {
        try {
          await api(`/api/notes/${n.id}`, { method: "PUT", body: JSON.stringify(vals) });
          setEditDialog(null);
          await refreshAll();
          setAppStatus("Note updated.", "success");
        } catch (err) { setAppStatus(`Update failed: ${err.message}`, "error"); }
      },
    });
  }

  /* ─── CRUD: Reminders ─── */
  async function submitReminder(e) {
    e.preventDefault();
    try {
      const payload = {
        message: reminderForm.message, channel: "telegram", target: reminderForm.target,
        remind_at: new Date(reminderForm.remindAt).toISOString(),
        is_recurring: reminderForm.recurring,
        recurrence_minutes: reminderForm.recurring && reminderForm.recurrenceMinutes ? Number(reminderForm.recurrenceMinutes) : null,
      };
      await api("/api/reminders", { method: "POST", body: JSON.stringify(payload) });
      setReminderForm({ message: "", target: defaultTarget, remindAt: toIsoLocalDateTime(15), recurring: false, recurrenceMinutes: "" });
      await refreshAll();
      setAppStatus("Reminder scheduled.", "success");
    } catch (err) { setAppStatus(`Reminder failed: ${err.message}`, "error"); }
  }

  async function sendNow(id) {
    try {
      await api(`/api/reminders/${id}/send-now`, { method: "POST" });
      await refreshAll();
      setAppStatus("Reminder sent.", "success");
    } catch (err) { setAppStatus(`Send failed: ${err.message}`, "error"); }
  }

  async function deleteReminder(id) {
    confirmAction("Delete this reminder permanently?", async () => {
      try {
        await api(`/api/reminders/${id}`, { method: "DELETE" });
        await refreshAll();
        setAppStatus("Reminder deleted.", "success");
      } catch (err) { setAppStatus(`Delete failed: ${err.message}`, "error"); }
    });
  }

  /* ─── Inbox Actions ─── */
  async function deleteInbox(id) {
    confirmAction("Delete this inbox item permanently?", async () => {
      try {
        await api(`/api/inbox/${id}`, { method: "DELETE" });
        await refreshAll();
        setAppStatus("Inbox item deleted.", "success");
      } catch (err) { setAppStatus(`Delete failed: ${err.message}`, "error"); }
    });
  }

  async function inboxToCapture(id) {
    try { await api(`/api/inbox/${id}/to-capture`, { method: "POST" }); await refreshAll(); setAppStatus("Promoted to capture.", "success"); }
    catch (err) { setAppStatus(`Promote failed: ${err.message}`, "error"); }
  }

  async function inboxToTask(id) {
    try {
      await api(`/api/inbox/${id}/to-task`, { method: "POST", body: JSON.stringify({ priority: "medium" }) });
      await refreshAll();
      setAppStatus("Promoted to task.", "success");
    } catch (err) { setAppStatus(`Promote failed: ${err.message}`, "error"); }
  }

  async function analyzeInbox(id) {
    try {
      setAppStatus("Analyzing…", "info");
      const resp = await api(`/api/inbox/${id}/analyze`, { method: "POST" });
      await refreshAll();
      setAppStatus(`Tagged: ${resp.tags}`, "success");
    } catch (err) { setAppStatus(`Analysis failed: ${err.message}`, "error"); }
  }

  function itemCanPreview(item) {
    return Boolean(item?.file_id && ["photo", "sticker", "animation"].includes(item.item_type));
  }

  function inboxFileName(item) {
    const extByType = {
      text: "txt",
      photo: "jpg",
      animation: "gif",
      sticker: "webp",
      video: "mp4",
      audio: "mp3",
      voice: "ogg",
      document: "file",
      unknown: "bin",
    };
    const ext = extByType[item?.item_type] || "bin";
    return `inbox_${item?.id || "item"}.${ext}`;
  }

  function inboxTypeLabel(item) {
    const labels = {
      text: "Text File",
      photo: "Image",
      animation: "GIF",
      sticker: "Sticker",
      video: "Video",
      audio: "Audio",
      voice: "Voice",
      document: "Document",
      location: "Location",
      unknown: "Unknown",
    };
    return labels[item?.item_type] || "File";
  }

  function inboxTypeIcon(item) {
    const icons = {
      text: "file-lock",
      photo: "activity",
      animation: "activity",
      sticker: "activity",
      video: "play",
      audio: "play",
      voice: "play",
      document: "download",
      location: "target",
      unknown: "inbox",
    };
    return icons[item?.item_type] || "inbox";
  }

  function itemHasFile(item) {
    return Boolean(item?.file_id || item?.item_type === "text");
  }

  function openInboxFile(id) {
    window.open(`/api/inbox/${id}/media`, "_blank", "noopener,noreferrer");
  }

  function renderInboxCard(item) {
    const hasDownload = itemHasFile(item);
    const canPreviewText = item.item_type === "text" || !itemCanPreview(item);

    return html`
      <div className="inbox-card" key=${item.id}>
        <button className="inbox-delete-btn btn-icon ghost" onClick=${() => deleteInbox(item.id)} title="Delete permanently" aria-label="Delete permanently">
          <${Icon} name="trash" size=${14} />
        </button>

        ${itemCanPreview(item) ? html`
          <img className="inbox-media-preview" src=${`/api/inbox/${item.id}/media`} alt="Inbox media" loading="lazy" onClick=${() => setInboxPreview(item)} />
        ` : ""}

        <div className="inbox-card-content">
          ${canPreviewText ? html`
            <div className="inbox-card-text" onClick=${() => setInboxPreview(item)} style=${{ cursor: "pointer" }}>
              ${item.text || html`<span className="muted">(no text payload)</span>`}
            </div>
          ` : (item.text ? html`
            <div className="inbox-card-text" onClick=${() => setInboxPreview(item)} style=${{ cursor: "pointer" }}>
              ${item.text}
            </div>
          ` : html`<div className="inbox-card-text muted" onClick=${() => setInboxPreview(item)} style=${{ cursor: "pointer" }}>(media message)</div>`)}

          <div className="inbox-card-meta">
            <span>${formatDate(item.created_at)}</span>
            <span>msg #${item.message_id}</span>
          </div>
        </div>

        <div className="inbox-card-actions" role="group" aria-label="Inbox item actions">
          <button className="btn-icon ghost sm" onClick=${() => setInboxPreview(item)} title="Preview" aria-label="Preview">
            <${Icon} name="search" size=${13} />
          </button>
          ${hasDownload ? html`
            <button className="btn-icon ghost sm" onClick=${() => openInboxFile(item.id)} title="Download" aria-label="Download">
              <${Icon} name="download" size=${13} />
            </button>
          ` : ""}
          <button className="btn-icon ghost sm" onClick=${() => inboxToCapture(item.id)} title="Promote to capture" aria-label="Promote to capture">
            <${Icon} name="pen-line" size=${13} />
          </button>
          <button className="btn-icon ghost sm" onClick=${() => inboxToTask(item.id)} title="Promote to task" aria-label="Promote to task">
            <${Icon} name="check-square" size=${13} />
          </button>
          <button className="btn-icon ghost sm" onClick=${() => analyzeInbox(item.id)} title="Analyze" aria-label="Analyze">
            <${Icon} name="settings" size=${13} />
          </button>
        </div>
      </div>
    `;
  }

  function renderInboxListItem(item) {
    const hasDownload = itemHasFile(item);
    const title = item.text || "(no text payload)";

    return html`
      <div className="list-item inbox-list-item" key=${item.id}>
        <div className="inbox-list-icon" onClick=${() => setInboxPreview(item)} title="Preview" aria-label="Preview">
          <${Icon} name=${inboxTypeIcon(item)} size=${14} />
        </div>
        <div className="list-item-content">
          <div className="list-item-title inbox-list-title" onClick=${() => setInboxPreview(item)} style=${{ cursor: "pointer" }}>
            ${title}
          </div>
          <div className="list-item-meta">
            <span><${Icon} name="clock" size=${12} /> ${formatDate(item.created_at)}</span>
            <span>msg #${item.message_id}</span>
          </div>
        </div>
        <div className="list-item-actions inbox-list-actions" role="group" aria-label="Inbox item actions">
          <button className="btn-icon ghost sm" onClick=${() => setInboxPreview(item)} title="Preview" aria-label="Preview">
            <${Icon} name="search" size=${13} />
          </button>
          ${hasDownload ? html`
            <button className="btn-icon ghost sm" onClick=${() => openInboxFile(item.id)} title="Download" aria-label="Download">
              <${Icon} name="download" size=${13} />
            </button>
          ` : ""}
          <button className="btn-icon ghost sm" onClick=${() => inboxToCapture(item.id)} title="Promote to capture" aria-label="Promote to capture">
            <${Icon} name="pen-line" size=${13} />
          </button>
          <button className="btn-icon ghost sm" onClick=${() => inboxToTask(item.id)} title="Promote to task" aria-label="Promote to task">
            <${Icon} name="check-square" size=${13} />
          </button>
          <button className="btn-icon ghost sm" onClick=${() => deleteInbox(item.id)} title="Delete permanently" aria-label="Delete permanently">
            <${Icon} name="trash" size=${13} />
          </button>
        </div>
      </div>
    `;
  }

  /* ─── Habits ─── */
  async function submitHabit(e) {
    e.preventDefault();
    try {
      await api("/api/habits", { method: "POST", body: JSON.stringify(habitForm) });
      setHabitForm({ name: "" });
      await refreshAll();
      setAppStatus("Habit created.", "success");
    } catch (err) { setAppStatus(`Habit failed: ${err.message}`, "error"); }
  }

  async function toggleHabit(id) {
    try {
      await api(`/api/habits/${id}/toggle`, { method: "POST", body: JSON.stringify({}) });
      await refreshAll();
    } catch (err) { setAppStatus(`Toggle failed: ${err.message}`, "error"); }
  }

  async function deleteHabit(id) {
    confirmAction("Remove this habit?", async () => {
      try {
        await api(`/api/habits/${id}`, { method: "DELETE" });
        await refreshAll();
        setAppStatus("Habit removed.", "success");
      } catch (err) { setAppStatus(`Delete failed: ${err.message}`, "error"); }
    });
  }

  /* ─── Export ─── */
  async function exportData() {
    try {
      setAppStatus("Preparing export…", "info");
      const resp = await api("/api/export");
      const blob = new Blob([JSON.stringify(resp, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `automation_hub_export_${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setAppStatus("Export downloaded.", "success");
    } catch (err) { setAppStatus(`Export failed: ${err.message}`, "error"); }
  }

  async function logout() {
    if (isMiniApp) {
      // In Mini App mode, close the app instead of navigating.
      sessionStorage.removeItem(keyStorage);
      sessionStorage.removeItem("miniapp_user");
      tgWebApp?.close?.();
      return;
    }
    await fetch("/auth/logout", { method: "POST" });
    window.location.href = "/";
  }

  /* ─── Filtering ─── */
  const filteredTasks = useMemo(() => {
    let items = taskFilter === "all" ? tasks : tasks.filter((t) => t.status === taskFilter);
    if (searchQuery && section === "tasks") {
      const q = searchQuery.toLowerCase();
      items = items.filter((t) => t.title.toLowerCase().includes(q));
    }
    return items;
  }, [tasks, taskFilter, searchQuery, section]);

  const filteredCaptures = useMemo(() => {
    if (!searchQuery || section !== "captures") return captures;
    const q = searchQuery.toLowerCase();
    return captures.filter((c) => c.content.toLowerCase().includes(q) || (c.url || "").toLowerCase().includes(q));
  }, [captures, searchQuery, section]);

  const filteredNotes = useMemo(() => {
    if (!searchQuery || section !== "notes") return notes;
    const q = searchQuery.toLowerCase();
    return notes.filter((n) => (n.title || "").toLowerCase().includes(q) || n.content.toLowerCase().includes(q));
  }, [notes, searchQuery, section]);

  const filteredReminders = useMemo(() => {
    if (!searchQuery || section !== "reminders") return reminders;
    const q = searchQuery.toLowerCase();
    return reminders.filter((r) => r.message.toLowerCase().includes(q));
  }, [reminders, searchQuery, section]);

  const filteredInbox = useMemo(() => {
    if (!searchQuery || section !== "inbox") return inboxItems;
    const q = searchQuery.toLowerCase();
    return inboxItems.filter((i) => (i.text || "").toLowerCase().includes(q) || i.item_type.toLowerCase().includes(q));
  }, [inboxItems, searchQuery, section]);

  /* ─── Computed stats ─── */
  const tasksDone = tasks.filter(t => t.status === "done").length;
  const tasksInProgress = tasks.filter(t => t.status === "in_progress").length;
  const tasksTotal = tasks.length;
  const remindersSent = reminders.filter(r => r.status === "sent").length;
  const remindersTotal = reminders.length;
  const habitsCompletedToday = habits.filter(h => h.completed_today).length;

  /* ─── Activity Feed (for overview) ─── */
  const activityFeed = useMemo(() => {
    const items = [];
    captures.slice(0, 5).forEach(c => items.push({ type: "capture", title: c.content, time: c.created_at, icon: "pen-line" }));
    tasks.slice(0, 5).forEach(t => items.push({ type: "task", title: t.title, time: t.created_at, icon: "check-square", extra: t.status }));
    notes.slice(0, 3).forEach(n => items.push({ type: "note", title: n.title || "Untitled Note", time: n.updated_at, icon: "file-lock" }));
    reminders.filter(r => r.sent_at).slice(0, 3).forEach(r => items.push({ type: "reminder", title: r.message, time: r.sent_at, icon: "bell", extra: "sent" }));
    items.sort((a, b) => new Date(b.time) - new Date(a.time));
    return items.slice(0, 10);
  }, [captures, tasks, notes, reminders]);

  /* ─── Render Helpers ─── */
  function renderEmptyState(iconName, title, hint, actionLabel = "", onAction) {
    return html`<div className="empty-state">
      <div className="empty-state-icon"><${Icon} name=${iconName} size=${28} /></div>
      <div className="empty-state-title">${title}</div>
      <div className="empty-state-hint">${hint}</div>
      ${actionLabel ? html`<button className="ghost sm" onClick=${onAction}>${actionLabel}</button>` : ""}
    </div>`;
  }

  /* ─── RENDER ─── */
  const meta = SECTION_META[section] || {};

  return html`
    <main className=${`app-shell density-${density}`}>

      <!-- Toasts -->
      <div className="toast-container">
        ${toasts.map(t => html`<div key=${t.id} className=${`toast ${t.kind}`}>${t.message}</div>`)}
      </div>

      <!-- Confirm Dialog -->
      ${confirmDialog && html`
        <${ConfirmDialog}
          message=${confirmDialog.message}
          onConfirm=${async () => { await confirmDialog.action(); setConfirmDialog(null); }}
          onCancel=${() => setConfirmDialog(null)}
        />
      `}

      <!-- Edit Dialog -->
      ${editDialog && html`
        <${EditModal}
          title=${editDialog.title}
          fields=${editDialog.fields}
          values=${editDialog.values}
          onSave=${editDialog.onSave}
          onCancel=${() => setEditDialog(null)}
        />
      `}

      ${inboxPreview && html`
        <${InboxPreviewModal}
          item=${inboxPreview}
          onClose=${() => setInboxPreview(null)}
        />
      `}

      <!-- Keyboard Shortcuts Modal -->
      ${showShortcuts && html`
        <div className="shortcuts-overlay" onClick=${() => setShowShortcuts(false)}>
          <div className="shortcuts-modal" onClick=${(e) => e.stopPropagation()}>
            <h3>⌨ Keyboard Shortcuts</h3>
            ${[
              ["?", "Toggle this panel"],
              ["/", "Focus search bar"],
              ["R", "Refresh all data"],
              ["D", "Toggle dark mode"],
              ["1–9", "Switch sections"],
              ["Esc", "Close menu / modal"],
            ].map(([key, desc]) => html`
              <div className="shortcut-row">
                <span>${desc}</span>
                <span className="shortcut-key">${key}</span>
              </div>`
            )}
          </div>
        </div>
      `}

      <div className="dashboard-layout">
        <!-- Sidebar Backdrop (mobile) -->
        ${sidebarOpen && window.innerWidth <= 900 ? html`<button className="sidebar-backdrop" onClick=${() => setSidebarOpen(false)} aria-label="Close menu"></button>` : ""}

        <!-- Sidebar -->
        <aside id="main-sidebar" className=${`panel sidebar ${sidebarOpen ? "open" : ""}`}>
          <div className="sidebar-brand">
            <div className="brand-icon"><${Icon} name="zap" size=${18} /></div>
            <div className="brand-text">
              <div className="brand-name">AutoHub</div>
              <div className="brand-subtitle">Command Center</div>
            </div>
          </div>

          <nav className="sidebar-nav">
            ${NAV_CONFIG.map((item) => html`
              <button
                key=${item.id}
                id=${`nav-${item.id}`}
                className=${`nav-link ${section === item.id ? "active" : ""}`}
                onClick=${() => openSection(item.id)}
              >
                <${Icon} name=${item.icon} size=${15} />
                ${item.label}
                ${item.id === "inbox" && inboxItems.length > 0 ? html`<span className="nav-badge pulse-badge">${inboxItems.length}</span>` : ""}
                ${item.id === "tasks" && tasks.filter(t => t.status !== "done").length > 0 ? html`<span className="nav-badge">${tasks.filter(t => t.status !== "done").length}</span>` : ""}
              </button>
            `)}
          </nav>

          <div className="sidebar-footer">
            ${isMiniApp ? html`
              <div className="sidebar-user-chip">
                <div className="sidebar-user-avatar">${(miniAppUser.first_name || "T").charAt(0).toUpperCase()}</div>
                <div className="sidebar-user-info">
                  <div className="sidebar-user-name">${miniAppUser.first_name || "Telegram User"}</div>
                  <div className="sidebar-user-role">Mini App</div>
                </div>
              </div>
            ` : html`
              <div className="sidebar-user-chip">
                <div className="sidebar-user-avatar">A</div>
                <div className="sidebar-user-info">
                  <div className="sidebar-user-name">Admin</div>
                  <div className="sidebar-user-role">Owner</div>
                </div>
              </div>
            `}
            <button className="nav-link" onClick=${logout} style=${{ color: isMiniApp ? "inherit" : "var(--red-600)" }}>
              <${Icon} name=${isMiniApp ? "x" : "log-out"} size=${15} />
              ${isMiniApp ? "Close App" : "Logout"}
            </button>
          </div>
        </aside>

        <!-- Main Content -->
        <section className="main-content">
          <!-- Topbar -->
          <header className="panel topbar">
            <div className="topbar-left">
              <button className="btn-icon ghost menu-toggle" onClick=${() => setSidebarOpen(v => !v)} aria-label="Toggle menu">
                <${Icon} name="menu" size=${18} />
              </button>
              <span className="topbar-section-title">${meta.title || "AutoHub"}</span>
              <span className="topbar-date">${new Date().toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</span>
            </div>
            <div className="topbar-right">
              <!-- Secondary nav: Habits, Pomodoro, Settings -->
              ${TOPBAR_EXTRA.map(item => html`
                <button
                  key=${item.id}
                  className=${`topbar-nav-btn ${section === item.id ? "active" : ""}`}
                  onClick=${() => openSection(item.id)}
                  title=${item.label}
                >
                  <${Icon} name=${item.icon} size=${16} />
                  ${item.id === "habits" && habits.length > 0 && habitsCompletedToday < habits.length ? html`<span className="topbar-nav-badge"></span>` : ""}
                </button>
              `)}
              <div className="topbar-sep"></div>
              ${!["summary", "settings", "pomodoro", "habits"].includes(section) ? html`
                <div className="search-bar">
                  <${Icon} name="search" size=${15} />
                  <input
                    ref=${searchRef}
                    type="text"
                    placeholder="Search…"
                    value=${searchQuery}
                    onInput=${(e) => setSearchQuery(e.target.value)}
                    style=${{ width: "160px", paddingLeft: "2.2rem" }}
                  />
                </div>
              ` : ""}
              <button className="topbar-nav-btn" onClick=${() => setDarkMode(v => !v)} title=${darkMode ? "Light mode" : "Dark mode"}>
                <${Icon} name=${darkMode ? "sun" : "moon"} size=${16} />
              </button>
              <button className="topbar-nav-btn" onClick=${refreshAll} disabled=${busy} title="Refresh">
                <${Icon} name="refresh-cw" size=${16} />
              </button>
              <div className=${`status-pill ${statusKind}`}>${busy ? "Syncing…" : status || "Ready"}</div>
            </div>
          </header>
            </div>
          </header>

          <!-- ═══ SUMMARY SECTION ═══ -->
          ${section === "summary" && html`
            <section className="panel section-panel" id="section-summary">
              <div className="section-head">
                <h2><${Icon} name="bar-chart" /> Today's Summary</h2>
                <p className="muted">Real-time snapshot of your operational health.</p>
              </div>
              <div className="summary-grid">
                <article className="summary-card card-green">
                  <div className="summary-card-icon"><${Icon} name="pen-line" size=${20} /></div>
                  <div className="summary-card-label">Captures Today</div>
                  <div className="summary-card-value">${summary?.captures_today ?? 0}</div>
                </article>
                <article className="summary-card card-amber">
                  <div className="summary-card-icon"><${Icon} name="check-square" size=${20} /></div>
                  <div className="summary-card-label">Open Tasks</div>
                  <div className="summary-card-value">${summary?.tasks_open ?? 0}</div>
                </article>
                <article className="summary-card card-blue">
                  <div className="summary-card-icon"><${Icon} name="bell" size=${20} /></div>
                  <div className="summary-card-label">Pending Reminders</div>
                  <div className="summary-card-value">${summary?.reminders_pending ?? 0}</div>
                </article>
                <article className="summary-card card-teal">
                  <div className="summary-card-icon"><${Icon} name="send" size=${20} /></div>
                  <div className="summary-card-label">Sent Today</div>
                  <div className="summary-card-value">${summary?.reminders_sent_today ?? 0}</div>
                </article>
                <article className="summary-card card-green">
                  <div className="summary-card-icon"><${Icon} name="file-lock" size=${20} /></div>
                  <div className="summary-card-label">Total Notes</div>
                  <div className="summary-card-value">${summary?.notes_total ?? 0}</div>
                </article>
                <article className="summary-card card-amber">
                  <div className="summary-card-icon"><${Icon} name="target" size=${20} /></div>
                  <div className="summary-card-label">Habits Today</div>
                  <div className="summary-card-value">${habitsCompletedToday}/${habits.length || 0}</div>
                </article>
              </div>
            </section>

            <!-- Progress Overview -->
            <section className="panel section-panel">
              <div className="section-head">
                <h2><${Icon} name="activity" /> Progress Tracker</h2>
                <p className="muted">Visual breakdown of your productivity.</p>
              </div>
              <div className="progress-grid">
                <${ProgressBar} value=${tasksDone} max=${tasksTotal} label="Tasks Completed" color="var(--green-500)" />
                <${ProgressBar} value=${tasksInProgress} max=${tasksTotal} label="Tasks In Progress" color="var(--amber-600)" />
                <${ProgressBar} value=${remindersSent} max=${remindersTotal} label="Reminders Delivered" color="var(--blue-600)" />
                <${ProgressBar} value=${habitsCompletedToday} max=${habits.length || 1} label="Habits Done Today" color="var(--teal-600)" />
              </div>
            </section>

            <!-- Quick Actions -->
            <section className="panel section-panel">
              <div className="section-head">
                <h2><${Icon} name="zap" /> Quick Actions</h2>
                <p className="muted">Capture ideas or create tasks without leaving the overview.</p>
              </div>
              <div className="quick-actions-grid">
                <form onSubmit=${submitCapture} className="quick-capture-bar">
                  <${Icon} name="pen-line" size=${18} />
                  <input required value=${captureForm.content} onInput=${(e) => setCaptureForm({ ...captureForm, content: e.target.value })} placeholder="Quick capture…" />
                  <button type="submit" className="sm" disabled=${busy}><${Icon} name="plus" size=${14} /> Capture</button>
                </form>
                <form onSubmit=${submitTask} className="quick-capture-bar">
                  <${Icon} name="check-square" size=${18} />
                  <input required value=${taskForm.title} onInput=${(e) => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="Quick task…" />
                  <button type="submit" className="sm" disabled=${busy}><${Icon} name="plus" size=${14} /> Task</button>
                </form>
              </div>
            </section>

            <!-- Activity Feed -->
            ${activityFeed.length > 0 && html`
              <section className="panel section-panel">
                <div className="section-head">
                  <h2><${Icon} name="activity" /> Recent Activity</h2>
                  <p className="muted">Timeline of your latest actions across all modules.</p>
                </div>
                <div className="list">
                  ${activityFeed.map((item, i) => html`
                    <div className="list-item" key=${i}>
                      <div className="list-item-content">
                        <div className="list-item-title">
                          <${Icon} name=${item.icon} size=${14} /> ${item.title.length > 80 ? item.title.substring(0, 80) + "…" : item.title}
                        </div>
                        <div className="list-item-meta">
                          <span className=${`status-badge ${item.extra || item.type}`}>${item.type}</span>
                          ${item.extra ? html`<span className=${`status-badge ${item.extra}`}>${item.extra}</span>` : ""}
                          <span>${relativeTime(item.time)}</span>
                        </div>
                      </div>
                    </div>
                  `)}
                </div>
              </section>
            `}
          `}

          <!-- ═══ CAPTURES SECTION ═══ -->
          ${section === "captures" && html`
            <section className="panel section-panel" id="section-captures">
              <div className="section-head">
                <h2><${Icon} name="pen-line" /> Quick Capture</h2>
                <p className="muted">Save context immediately before it gets lost.</p>
              </div>
              <form onSubmit=${submitCapture} className="stack">
                <textarea required value=${captureForm.content} onInput=${(e) => setCaptureForm({ ...captureForm, content: e.target.value })} placeholder="Idea, thought, insight, or context…" rows="3" />
                <input type="url" value=${captureForm.url} onInput=${(e) => setCaptureForm({ ...captureForm, url: e.target.value })} placeholder="Optional URL reference" />
                <button disabled=${busy}><${Icon} name="plus" size=${16} /> Save Capture</button>
              </form>
              <div style=${{ marginTop: "1.25rem" }}>
                ${filteredCaptures.length > 0 ? html`
                  <div className="list">
                    ${filteredCaptures.map(c => html`
                      <div className="list-item" key=${c.id}>
                        <div className="list-item-content">
                          <div className="list-item-title">${c.content}</div>
                          <div className="list-item-meta">
                            ${c.url ? html`<span><${Icon} name="link" size=${12} /> <a href=${c.url} target="_blank" rel="noopener">${c.url.length > 50 ? c.url.substring(0, 50) + "…" : c.url}</a></span>` : ""}
                            <span><${Icon} name="clock" size=${12} /> ${formatDate(c.created_at)}</span>
                          </div>
                        </div>
                        <div className="list-item-actions">
                          <button className="btn-icon ghost sm" onClick=${() => { copyToClipboard(c.content); setAppStatus("Copied to clipboard.", "success"); }} title="Copy">
                            <${Icon} name="copy" size=${14} />
                          </button>
                          <button className="btn-icon ghost sm" onClick=${() => editCapture(c)} title="Edit">
                            <${Icon} name="edit" size=${14} />
                          </button>
                          <button className="btn-icon danger-ghost sm" onClick=${() => deleteCapture(c.id)} title="Delete">
                            <${Icon} name="trash" size=${14} />
                          </button>
                        </div>
                      </div>
                    `)}
                  </div>
                ` : renderEmptyState("pen-line", "No captures yet", "Use the form above to save your first idea.", "Focus Form", () => document.querySelector(".section-panel textarea")?.focus())}
              </div>
            </section>
          `}

          <!-- ═══ INBOX SECTION ═══ -->
          ${section === "inbox" && html`
            <section className="panel section-panel" id="section-inbox">
              <div className="section-head">
                <div className="section-head-row">
                  <div>
                    <h2><${Icon} name="inbox" /> Telegram Inbox</h2>
                    <p className="muted">Anything shared to your Telegram bot lands here automatically.</p>
                  </div>
                  <div className="inbox-head-actions">
                    ${inboxItems.length > 0 ? html`<span className="muted">${inboxItems.length} item${inboxItems.length !== 1 ? "s" : ""}</span>` : ""}
                    <div className="inbox-view-toggle" role="group" aria-label="Inbox view">
                      <button className=${`ghost sm btn-icon ${inboxView === "list" ? "active" : ""}`} onClick=${() => setInboxView("list")} title="List view" aria-label="List view">
                        <${Icon} name="menu" size=${13} />
                      </button>
                      <button className=${`ghost sm btn-icon ${inboxView === "cards" ? "active" : ""}`} onClick=${() => setInboxView("cards")} title="Card view" aria-label="Card view">
                        <${Icon} name="layout-dashboard" size=${13} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              ${busy && filteredInbox.length === 0 ? html`
                ${inboxView === "list" ? html`
                  <div className="list inbox-list">
                    ${[1, 2, 3, 4].map((n) => html`
                      <div className="list-item inbox-list-item inbox-list-skeleton" key=${`skeleton-list-${n}`}>
                        <span className="inbox-skeleton-dot"></span>
                        <div className="list-item-content">
                          <div className="inbox-skeleton-line w-60"></div>
                          <div className="inbox-skeleton-line w-100"></div>
                        </div>
                        <div className="list-item-actions inbox-list-actions">
                          <span className="inbox-skeleton-dot"></span>
                          <span className="inbox-skeleton-dot"></span>
                          <span className="inbox-skeleton-dot"></span>
                        </div>
                      </div>
                    `)}
                  </div>
                ` : html`
                  <div className="inbox-grid">
                    ${[1, 2, 3].map((n) => html`
                      <div className="inbox-card inbox-card-skeleton" key=${`skeleton-${n}`}>
                        <div className="inbox-media-placeholder"></div>
                        <div className="inbox-card-content">
                          <div className="inbox-skeleton-line w-60"></div>
                          <div className="inbox-skeleton-line w-100"></div>
                          <div className="inbox-skeleton-line w-80"></div>
                        </div>
                        <div className="inbox-card-actions">
                          <span className="inbox-skeleton-dot"></span>
                          <span className="inbox-skeleton-dot"></span>
                          <span className="inbox-skeleton-dot"></span>
                        </div>
                      </div>
                    `)}
                  </div>
                `}
              ` : filteredInbox.length > 0 ? html`
                ${inboxView === "list" ? html`
                  <div className="list inbox-list">
                    ${filteredInbox.map((item) => renderInboxListItem(item))}
                  </div>
                ` : html`
                  <div className="inbox-grid">
                    ${filteredInbox.map((item) => renderInboxCard(item))}
                  </div>
                `}
              ` : renderEmptyState("inbox", "Inbox is empty", "Send text, photos, or files to your Telegram bot to see them here.", "Refresh", refreshAll)}
            </section>
          `}

          <!-- ═══ TASKS + REMINDERS SECTION ═══ -->
          ${section === "tasks" && html`
            <section className="panel section-panel" id="section-tasks">
              <div className="section-head">
                <h2><${Icon} name="check-square" /> Tasks & Reminders</h2>
                <p className="muted">Track work and schedule Telegram reminders — all in one place.</p>
              </div>

              <!-- Sub-tab switcher -->
              <div className="sub-tab-bar">
                <button
                  className=${`sub-tab ${taskSubTab === "tasks" ? "active" : ""}`}
                  onClick=${() => setTaskSubTab("tasks")}
                >
                  <${Icon} name="check-square" size=${13} /> Tasks
                  ${tasks.filter(t => t.status !== "done").length > 0 ? ` (${tasks.filter(t => t.status !== "done").length} open)` : ""}
                </button>
                <button
                  className=${`sub-tab ${taskSubTab === "reminders" ? "active" : ""}`}
                  onClick=${() => setTaskSubTab("reminders")}
                >
                  <${Icon} name="bell" size=${13} /> Reminders
                  ${reminders.filter(r => r.status === "pending").length > 0 ? ` (${reminders.filter(r => r.status === "pending").length} pending)` : ""}
                </button>
              </div>

              <!-- TASKS TAB -->
              ${taskSubTab === "tasks" && html`
                <form onSubmit=${submitTask} className="stack">
                  <input required value=${taskForm.title} onInput=${(e) => setTaskForm({ ...taskForm, title: e.target.value })} placeholder="What needs to be done?" />
                  <div className="row row-2">
                    <select value=${taskForm.priority} onChange=${(e) => setTaskForm({ ...taskForm, priority: e.target.value })}>
                      <option value="low">Low Priority</option>
                      <option value="medium">Medium Priority</option>
                      <option value="high">High Priority</option>
                    </select>
                    <input type="date" value=${taskForm.dueDate} onInput=${(e) => setTaskForm({ ...taskForm, dueDate: e.target.value })} />
                  </div>
                  <button disabled=${busy}><${Icon} name="plus" size=${16} /> Add Task</button>
                </form>

                <div className="filter-row" style=${{ marginTop: "1rem" }}>
                  ${["all", "todo", "in_progress", "done"].map(f => html`
                    <button key=${f} className=${`ghost sm ${taskFilter === f ? "active" : ""}`} onClick=${() => setTaskFilter(f)}>
                      ${f === "all" ? "All" : f === "todo" ? "To Do" : f === "in_progress" ? "In Progress" : "Done"} ${f !== "all" ? `(${tasks.filter(t => t.status === f).length})` : `(${tasks.length})`}
                    </button>
                  `)}
                </div>

                ${tasksTotal > 0 ? html`
                  <div style=${{ margin: "0.75rem 0 0.25rem" }}>
                    <${ProgressBar} value=${tasksDone} max=${tasksTotal} label="Completion" color="var(--green-500)" />
                  </div>
                ` : ""}

                <div style=${{ marginTop: "0.5rem" }}>
                  ${filteredTasks.length > 0 ? html`
                    <div className="list">
                      ${filteredTasks.map(t => html`
                        <div className="list-item" key=${t.id}>
                          <button
                            className=${`btn-icon ${t.status === "done" ? "success-ghost" : "ghost"}`}
                            onClick=${() => toggleTask(t)}
                            title=${t.status === "done" ? "Mark as Todo" : t.status === "todo" ? "Start Working" : "Mark as Done"}
                            style=${{ flexShrink: 0 }}
                          >
                            <${Icon} name=${t.status === "done" ? "check" : t.status === "in_progress" ? "loader" : "check-square"} size=${16} />
                          </button>
                          <div className="list-item-content">
                            <div className=${`list-item-title ${t.status === "done" ? "done" : ""}`}>${t.title}</div>
                            <div className="list-item-meta">
                              <span className=${`priority-badge ${t.priority}`}>${t.priority}</span>
                              <span className=${`status-badge ${t.status}`}>${t.status === "in_progress" ? "in progress" : t.status}</span>
                              ${t.due_date ? html`<span><${Icon} name="clock" size=${12} /> ${formatDateShort(t.due_date)}</span>` : ""}
                            </div>
                            ${t.status !== "done" ? html`
                              <div className="task-quick-status" style=${{ marginTop: "0.35rem" }}>
                                ${t.status !== "todo" ? html`<button className="ghost sm" onClick=${() => setTaskStatus(t, "todo")}><${Icon} name="undo" size=${11} /> To Do</button>` : ""}
                                ${t.status !== "in_progress" ? html`<button className="ghost sm" onClick=${() => setTaskStatus(t, "in_progress")}><${Icon} name="loader" size=${11} /> In Progress</button>` : ""}
                                ${t.status !== "done" ? html`<button className="success-ghost sm" onClick=${() => setTaskStatus(t, "done")}><${Icon} name="check" size=${11} /> Done</button>` : ""}
                              </div>
                            ` : ""}
                          </div>
                          <div className="list-item-actions">
                            <button className="btn-icon ghost sm" onClick=${() => editTask(t)} title="Edit"><${Icon} name="edit" size=${14} /></button>
                            <button className="btn-icon danger-ghost sm" onClick=${() => deleteTask(t.id)} title="Delete"><${Icon} name="trash" size=${14} /></button>
                          </div>
                        </div>
                      `)}
                    </div>
                  ` : renderEmptyState("check-square", "No tasks in this filter", "Add a task to get started tracking your work.", "Focus Form", () => document.querySelector(".section-panel input")?.focus())}
                </div>
              `}

              <!-- REMINDERS TAB -->
              ${taskSubTab === "reminders" && html`
                <form onSubmit=${submitReminder} className="stack">
                  <input required value=${reminderForm.message} onInput=${(e) => setReminderForm({ ...reminderForm, message: e.target.value })} placeholder="Reminder message" />
                  <input required value=${reminderForm.target} onInput=${(e) => setReminderForm({ ...reminderForm, target: e.target.value })} placeholder="Telegram chat ID" />
                  <input type="datetime-local" required value=${reminderForm.remindAt} onInput=${(e) => setReminderForm({ ...reminderForm, remindAt: e.target.value })} />
                  <div className="flex-row">
                    ${[
                      { label: "+15m", mins: 15 }, { label: "+30m", mins: 30 },
                      { label: "+1h", mins: 60 }, { label: "+3h", mins: 180 },
                      { label: "Tomorrow 9am", mins: null },
                    ].map(p => html`
                      <button key=${p.label} className="ghost sm" onClick=${(e) => {
                        e.preventDefault();
                        if (p.mins !== null) {
                          setReminderForm({ ...reminderForm, remindAt: toIsoLocalDateTime(p.mins) });
                        } else {
                          const t = new Date(); t.setDate(t.getDate() + 1); t.setHours(9, 0, 0, 0);
                          const yyyy = t.getFullYear(), mm = String(t.getMonth()+1).padStart(2,"0"), dd = String(t.getDate()).padStart(2,"0");
                          setReminderForm({ ...reminderForm, remindAt: `${yyyy}-${mm}-${dd}T09:00` });
                        }
                      }}><${Icon} name="clock" size=${12} /> ${p.label}</button>
                    `)}
                  </div>
                  <label className="inline-check">
                    <input type="checkbox" checked=${reminderForm.recurring} onChange=${(e) => setReminderForm({ ...reminderForm, recurring: e.target.checked })} />
                    <${Icon} name="repeat" size=${14} /> Repeat this reminder
                  </label>
                  ${reminderForm.recurring && html`<input type="number" min="1" placeholder="Recurrence interval (minutes)" value=${reminderForm.recurrenceMinutes} onInput=${(e) => setReminderForm({ ...reminderForm, recurrenceMinutes: e.target.value })} />`}
                  <button disabled=${busy}><${Icon} name="bell" size=${16} /> Schedule Reminder</button>
                </form>

                <div style=${{ marginTop: "1.25rem" }}>
                  ${filteredReminders.length > 0 ? html`
                    <div className="list">
                      ${filteredReminders.map(r => html`
                        <div className="list-item" key=${r.id}>
                          <div className="list-item-content">
                            <div className="list-item-title">${r.message}</div>
                            <div className="list-item-meta">
                              <span className=${`status-badge ${r.status}`}>${r.status}</span>
                              <span><${Icon} name="send" size=${12} /> ${r.channel} → ${r.target}</span>
                              <span><${Icon} name="clock" size=${12} /> ${formatDate(r.remind_at)} (${relativeTime(r.remind_at)})</span>
                              ${r.is_recurring ? html`<span><${Icon} name="repeat" size=${12} /> every ${r.recurrence_minutes}m</span>` : ""}
                              ${r.last_error ? html`<span class="error-text" title=${r.last_error}>⚠ error</span>` : ""}
                            </div>
                          </div>
                          <div className="list-item-actions">
                            ${r.status === "pending" ? html`
                              <button className="success-ghost sm" onClick=${() => sendNow(r.id)} title="Send Now"><${Icon} name="send" size=${14} /> Send</button>
                            ` : ""}
                            <button className="btn-icon danger-ghost sm" onClick=${() => deleteReminder(r.id)} title="Delete"><${Icon} name="trash" size=${14} /></button>
                          </div>
                        </div>
                      `)}
                    </div>
                  ` : renderEmptyState("bell", "No reminders yet", "Schedule your first reminder using the form above.", "Focus Form", () => document.querySelector(".section-panel input")?.focus())}
                </div>
              `}
            </section>
          `}


          <!-- ═══ NOTES SECTION ═══ -->
          ${section === "notes" && html`
            <section className="panel section-panel" id="section-notes">
              <div className="section-head">
                <h2><${Icon} name="file-lock" /> Encrypted Notes</h2>
                <p className="muted">Your notes are encrypted at rest for maximum privacy.</p>
              </div>
              <form onSubmit=${submitNote} className="stack">
                <input value=${noteForm.title} onInput=${(e) => setNoteForm({ ...noteForm, title: e.target.value })} placeholder="Note title (optional)" />
                <div style=${{ position: "relative" }}>
                  <textarea required value=${noteForm.content} onInput=${(e) => setNoteForm({ ...noteForm, content: e.target.value })} placeholder="Write your private note here…" rows="4" />
                  ${noteForm.content.length > 0 ? html`
                    <div className="char-count">${noteForm.content.length} chars · ${noteForm.content.split(/\s+/).filter(Boolean).length} words</div>
                  ` : ""}
                </div>
                <button disabled=${busy}><${Icon} name="save" size=${16} /> Save Encrypted Note</button>
              </form>
              <div style=${{ marginTop: "1.25rem" }}>
                ${filteredNotes.length > 0 ? html`
                  <div className="list">
                    ${filteredNotes.map(n => html`
                      <div className="list-item" key=${n.id}>
                        <div className="list-item-content">
                          <div className="list-item-title">${n.title || "Untitled Note"}</div>
                          <div style=${{ color: "var(--text-secondary)", fontSize: "0.88rem", whiteSpace: "pre-wrap", marginTop: "0.3rem", lineHeight: 1.6 }}>${n.content}</div>
                          <div className="list-item-meta" style=${{ marginTop: "0.5rem" }}>
                            <span><${Icon} name="clock" size=${12} /> Updated ${formatDate(n.updated_at)}</span>
                            <span>${n.content.length} chars</span>
                          </div>
                        </div>
                        <div className="list-item-actions">
                          <button className="btn-icon ghost sm" onClick=${() => { copyToClipboard(n.content); setAppStatus("Note copied.", "success"); }} title="Copy">
                            <${Icon} name="copy" size=${14} />
                          </button>
                          <button className="btn-icon ghost sm" onClick=${() => editNote(n)} title="Edit">
                            <${Icon} name="edit" size=${14} />
                          </button>
                          <button className="btn-icon danger-ghost sm" onClick=${() => deleteNote(n.id)} title="Delete">
                            <${Icon} name="trash" size=${14} />
                          </button>
                        </div>
                      </div>
                    `)}
                  </div>
                ` : renderEmptyState("file-lock", "No notes yet", "Create your first encrypted note above.", "Focus Form", () => document.querySelector(".section-panel input")?.focus())}
              </div>
            </section>
          `}


          <!-- ═══ HABITS SECTION ═══ -->
          ${section === "habits" && html`
            <section className="panel section-panel" id="section-habits">
              <div className="section-head">
                <h2><${Icon} name="target" /> Habit Tracker</h2>
                <p className="muted">Build consistency with daily habit tracking and streak counting.</p>
              </div>
              <form onSubmit=${submitHabit} className="quick-capture-bar">
                <${Icon} name="plus" size=${18} />
                <input required value=${habitForm.name} onInput=${(e) => setHabitForm({ ...habitForm, name: e.target.value })} placeholder="New habit name… (e.g., Exercise, Read, Meditate)" />
                <button type="submit" className="sm" disabled=${busy}><${Icon} name="plus" size=${14} /> Add Habit</button>
              </form>

              <div style=${{ marginTop: "1.25rem" }}>
                ${habits.length > 0 ? html`
                  <div className="habits-grid">
                    ${habits.map(h => html`
                      <div className=${`habit-card ${h.completed_today ? "completed" : ""}`} key=${h.id}>
                        <div className="habit-card-main" onClick=${() => toggleHabit(h.id)}>
                          <div className=${`habit-check ${h.completed_today ? "checked" : ""}`}>
                            ${h.completed_today ? html`<${Icon} name="check" size=${18} />` : ""}
                          </div>
                          <div className="habit-info">
                            <div className="habit-name">${h.name}</div>
                            <div className="habit-streak">
                              <${Icon} name="flame" size=${12} />
                              ${h.streak > 0 ? `${h.streak} day streak` : "No streak yet"}
                            </div>
                          </div>
                        </div>
                        <button className="btn-icon danger-ghost sm" onClick=${() => deleteHabit(h.id)} title="Remove">
                          <${Icon} name="x" size=${14} />
                        </button>
                      </div>
                    `)}
                  </div>
                ` : renderEmptyState("target", "No habits yet", "Create your first habit to start tracking daily consistency.", "Focus Form", () => document.querySelector(".quick-capture-bar input")?.focus())}
              </div>

              ${habits.length > 0 ? html`
                <div className="habit-summary-bar">
                  <span><${Icon} name="target" size=${14} /> ${habitsCompletedToday} of ${habits.length} completed today</span>
                  <${ProgressBar} value=${habitsCompletedToday} max=${habits.length} label="" color="var(--green-500)" />
                </div>
              ` : ""}
            </section>
          `}

          <!-- ═══ POMODORO SECTION ═══ -->
          ${section === "pomodoro" && html`<${PomodoroTimer} addToast=${addToast} />`}

          <!-- ═══ SETTINGS SECTION ═══ -->
          ${section === "settings" && html`
            <section className="panel section-panel" id="section-settings">
              <div className="section-head">
                <h2><${Icon} name="settings" /> Settings</h2>
                <p className="muted">Configure access credentials and workspace preferences.</p>
              </div>
              <div className="stack" style=${{ maxWidth: "480px" }}>
                <div>
                  <div className="field-label">API Key (optional)</div>
                  <p className="muted" style=${{ marginBottom: "0.5rem", fontSize: "0.82rem" }}>For external API clients. Telegram session auth is the primary login method.</p>
                  <input type="password" placeholder="Paste your X-API-Key" value=${apiKey} onInput=${(e) => setApiKey(e.target.value)} />
                </div>
                <button
                  className="ghost"
                  onClick=${() => {
                    localStorage.setItem(keyStorage, apiKey.trim());
                    setAppStatus(apiKey.trim() ? "API key saved." : "API key cleared.", "success");
                  }}
                >
                  <${Icon} name="key" size=${16} /> ${apiKey.trim() ? "Save API Key" : "Clear API Key"}
                </button>

                <div className="sidebar-divider" style=${{ margin: "0.5rem 0" }}></div>

                <div>
                  <div className="field-label">Appearance</div>
                  <div className="flex-row">
                    <button className=${`ghost sm ${!darkMode ? "active" : ""}`} onClick=${() => setDarkMode(false)}>
                      <${Icon} name="sun" size=${14} /> Light
                    </button>
                    <button className=${`ghost sm ${darkMode ? "active" : ""}`} onClick=${() => setDarkMode(true)}>
                      <${Icon} name="moon" size=${14} /> Dark
                    </button>
                  </div>
                </div>

                <div className="sidebar-divider" style=${{ margin: "0.5rem 0" }}></div>

                <div>
                  <div className="field-label">Density</div>
                  <div className="flex-row">
                    <button className=${`ghost sm ${density === "comfortable" ? "active" : ""}`} onClick=${() => setDensity("comfortable")}>Comfortable</button>
                    <button className=${`ghost sm ${density === "compact" ? "active" : ""}`} onClick=${() => setDensity("compact")}>Compact</button>
                  </div>
                </div>

                <div className="sidebar-divider" style=${{ margin: "0.5rem 0" }}></div>

                <div>
                  <div className="field-label">Auto-Refresh</div>
                  <p className="muted" style=${{ marginBottom: "0.5rem", fontSize: "0.82rem" }}>Automatically refresh data every 60 seconds.</p>
                  <label className="inline-check">
                    <input type="checkbox" checked=${autoRefresh} onChange=${(e) => setAutoRefresh(e.target.checked)} />
                    Enable auto-refresh
                  </label>
                </div>

                <div className="sidebar-divider" style=${{ margin: "0.5rem 0" }}></div>

                <div>
                  <div className="field-label">Data Management</div>
                  <button className="ghost" onClick=${exportData}>
                    <${Icon} name="download" size=${16} /> Export All Data (JSON)
                  </button>
                </div>

                <div className="sidebar-divider" style=${{ margin: "0.5rem 0" }}></div>

                <button className="danger-ghost" onClick=${logout}>
                  <${Icon} name="log-out" size=${16} /> Logout
                </button>
              </div>
            </section>
          `}

        </section>
      </div>
    </main>
  `;
}

createRoot(rootEl).render(html`<${App} />`);
