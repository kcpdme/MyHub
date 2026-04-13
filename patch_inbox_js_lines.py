with open("app/static/react-app.js", "r") as f:
    lines = f.readlines()

new_lines = lines[:1315] + [
"""                <div className="inbox-grid">
                  ${filteredInbox.map(item => html`
                    <div className="inbox-card" key=${item.id}>
                      <button className="inbox-delete-btn" onClick=${() => deleteInbox(item.id)} title="Delete permanently">
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
                            <${Icon} name="download" size=${13} /> Download
                          </button>
                        ` : ""}
                        <button className="ghost sm" onClick=${() => inboxToCapture(item.id)}>
                          <${Icon} name="pen-line" size=${13} /> Capture
                        </button>
                      </div>
                    </div>
                  `)}
                </div>
"""
] + lines[1365:]

with open("app/static/react-app.js", "w") as f:
    f.writelines(new_lines)
print("done")
