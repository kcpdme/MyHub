import re

with open("app/static/react-app.js", "r") as f:
    text = f.read()

# 1. Add toasts state and addToast function
state_vars = """
  const [section, setSection] = useState(localStorage.getItem("hub_section") || "summary");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apiKey, setApiKey] = useState(localStorage.getItem(keyStorage) || "");
  const [status, setStatus] = useState("");
  const [statusKind, setStatusKind] = useState("info");
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState([]);"""

# Remove old state
text = re.sub(r'const \[section, setSection\].*?const \[busy, setBusy\] = useState\(false\);', state_vars.strip(), text, flags=re.DOTALL)

# Add addToast
setAppStatus_def = """  function addToast(message, kind = "info") {
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
  }"""

text = re.sub(r'function setAppStatus\(message, kind = "info"\) {.*?setStatusKind\(kind\);\n  }', setAppStatus_def, text, flags=re.DOTALL)

# Update inbox section
old_inbox = 'className="list inbox-list"'
new_inbox = 'className="inbox-grid"'
text = text.replace(old_inbox, new_inbox)

# Add skeleton logic
old_inbox_items = """              ${inboxItems.map(
                (item) => html`<li>
                  <div className="inbox-headline">
                    <strong>${item.item_type.toUpperCase()}</strong>
                    <span className="muted">#${item.id}</span>
                  </div>
                  ${itemCanPreview(item)
                    ? html`<img className="inbox-thumb" src=${`/api/inbox/${item.id}/media`} alt="Inbox media" loading="lazy" />`
                    : ""}
                  <div>${item.text || "(no text)"}</div>
                  <div className="muted">${formatDate(item.created_at)} | msg #${item.message_id}</div>
                  <div className="row">
                    <button className="ghost" onClick=${() => inboxToCapture(item.id)}>To Capture</button>
                    <button className="ghost" onClick=${() => inboxToTask(item.id)}>To Task</button>
                    <button className="ghost" onClick=${() => archiveInbox(item.id)}>Archive</button>
                  </div>
                </li>`,
              )}
              ${inboxItems.length === 0 && html`<li className="muted">No inbox items yet. Send text, photos, or files to your bot.</li>`}"""

new_inbox_items = """              ${busy && inboxItems.length === 0 ? 
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
                    <div style=${{display: "flex", gap: "0.5rem", alignItems: "center"}}>
                      <span className="muted">#${item.id}</span>
                      <button style=${{padding: "0.2rem 0.5rem", fontSize: "0.8rem", width: "auto"}} className="ghost" onClick=${() => analyzeInbox(item.id)}>✨ Auto-Tag</button>
                    </div>
                  </div>
                  ${itemCanPreview(item)
                    ? html`<img className="inbox-thumb" src=${`/api/inbox/${item.id}/media`} alt="Inbox media" loading="lazy" />`
                    : ""}
                  <div style=${{whiteSpace: "pre-wrap", margin: "0.5rem 0", lineHeight: "1.6"}}>${item.text || "(no text)"}</div>
                  <div className="muted" style=${{fontSize: "0.85rem"}}>${formatDate(item.created_at)} | msg #${item.message_id}</div>
                  <div className="row" style=${{marginTop: "0.8rem"}}>
                    <button className="ghost" onClick=${() => inboxToCapture(item.id)}>To Capture</button>
                    <button className="ghost" onClick=${() => inboxToTask(item.id)}>To Task</button>
                    <button className="ghost" onClick=${() => archiveInbox(item.id)}>Archive</button>
                  </div>
                </li>`)
              }
              ${!busy && inboxItems.length === 0 && html`<li className="muted" style=${{gridColumn: "1 / -1", textAlign: "center", padding: "3rem"}}>No inbox items yet. Send text, photos, or files to your bot.</li>`}"""

text = text.replace(old_inbox_items, new_inbox_items)

# Add analyzeInbox function Next to archiveInbox
analyze_fn = """  async function analyzeInbox(id) {
    try {
      setAppStatus("Analyzing item with AI...", "info");
      const resp = await api(`/api/inbox/${id}/analyze`, { method: "POST" });
      await refreshAll();
      setAppStatus(`Item categorized: ${resp.tags}`, "success");
    } catch (err) {
      setAppStatus(`Analysis failed: ${err.message}`, "error");
    }
  }

  async function archiveInbox(id) {"""

text = text.replace('  async function archiveInbox(id) {', analyze_fn)

# Add Toasts to layout
toasts_dom = """    <main className="app-shell">
      <div className="toast-container">
        ${toasts.map(t => html`<div key=${t.id} className=${`toast ${t.kind}`}>${t.message}</div>`)}
      </div>"""

text = text.replace('<main className="app-shell">', toasts_dom)

with open("app/static/react-app.js", "w") as f:
    f.write(text)

