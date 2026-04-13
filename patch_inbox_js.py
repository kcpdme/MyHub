import re

with open("app/static/react-app.js", "r") as f:
    content = f.read()

# Replace the inbox grid mapped area 
# From <div className="inbox-grid"> to </div> /* end of map */
pattern = re.compile(r'\<div className="inbox-grid"\>.*?`\)\}\s*\<\/div\>', re.DOTALL)

replacement = """\
<div className="inbox-grid">
                  ${filteredInbox.map(item => html`
                    <div className="inbox-card" key=${item.id}>
                      <button className="inbox-delete-btn" onClick=${() => deleteInbox(item.id)} title="Delete permanently" aria-label="Delete permanently">
                        <${Icon} name="trash" size=${14} />
                      </button>

                      ${itemCanPreview(item) ? html`
                        <img className="inbox-media-preview" src=${`/api/inbox/${item.id}/media`} alt="Inbox media" loading="lazy" onClick=${() => setInboxPreview(item)} />
                      ` : ""}

                      <div className="inbox-card-content">
                        ${item.item_type === "text" || !itemCanPreview(item) ? html`
                          <div className="inbox-card-text" onClick=${() => setInboxPreview(item)} style=${{ cursor: "pointer" }}>
                            ${item.text || html`<span className="muted">(no text payload)</span>`}
                          </div>
                        ` : (item.text ? html`
                            <div className="inbox-card-text" onClick=${() => setInboxPreview(item)} style=${{ cursor: "pointer" }}>
                              ${item.text}
                            </div>
                        ` : "")}

                        <div className="inbox-card-meta">
                          <span className="inbox-type-badge">
                            <${Icon} name=${inboxTypeIcon(item)} size=${10} />
                            ${inboxTypeLabel(item)}
                          </span>
                          <span>${formatDate(item.created_at)}</span>
                        </div>
                      </div>

                      <div className="inbox-card-actions">
                        <button className="ghost sm" onClick=${() => setInboxPreview(item)}>
                          <${Icon} name="search" size=${13} /> Preview
                        </button>
                        ${itemHasFile(item) && item.item_type !== "text" ? html`
                          <button className="ghost sm" onClick=${() => openInboxFile(item.id)}>
                            <${Icon} name="download" size=${13} /> Open
                          </button>
                        ` : ""}
                        <button className="ghost sm" onClick=${() => inboxToCapture(item.id)}>
                          <${Icon} name="pen-line" size=${13} /> Capture
                        </button>
                      </div>
                    </div>
                  `)}
                </div>"""

new_content = pattern.sub(replacement, content, count=1)
if new_content != content:
    with open("app/static/react-app.js", "w") as f:
        f.write(new_content)
    print("Patched react-app.js")
else:
    print("Failed to patch react-app.js")

