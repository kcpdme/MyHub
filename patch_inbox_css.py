import re

with open("app/static/style.css", "r") as f:
    content = f.read()

# Regex to match from .inbox-grid { ... to .inbox-preview-text
pattern = re.compile(r'\.inbox-grid \{.*?(?=\.inbox-preview-modal \{)', re.DOTALL)

replacement = """\
.inbox-grid {
  columns: 3 280px;
  column-gap: 1rem;
}
.inbox-card {
  break-inside: avoid;
  margin-bottom: 1rem;
  background: var(--surface);
  border: 1px solid var(--line-soft);
  border-radius: var(--r-12);
  box-shadow: var(--sh-xs);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  transition: transform var(--fast), box-shadow var(--fast);
}
.inbox-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--sh-md);
  border-color: var(--line);
}
.inbox-media-preview {
  width: 100%;
  max-height: 300px;
  object-fit: cover;
  display: block;
  background: var(--surface-2);
  border-bottom: 1px solid var(--line-soft);
  cursor: pointer;
}
.inbox-card-content {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.inbox-card-text {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--ink-1);
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 8;
  -webkit-box-orient: vertical;
}
.inbox-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.72rem;
  color: var(--ink-3);
  margin-top: 0.2rem;
}
.inbox-card-actions {
  display: flex;
  gap: 0.4rem;
  padding: 0.5rem 1rem 1rem;
  border-top: none;
  background: transparent;
  flex-wrap: wrap;
}
.inbox-card-actions button {
  flex: 1;
  justify-content: center;
}
.inbox-delete-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  background: rgba(0,0,0,0.4);
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity var(--fast), background var(--fast);
  backdrop-filter: blur(4px);
  z-index: 10;
}
.inbox-card:hover .inbox-delete-btn {
  opacity: 1;
}
.inbox-delete-btn:hover {
  background: rgba(220, 38, 38, 0.8);
}
.inbox-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.5rem;
  background: var(--surface-2);
  border: 1px solid var(--line-soft);
  border-radius: var(--r-full);
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--ink-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
"""

new_content = pattern.sub(replacement, content)
with open("app/static/style.css", "w") as f:
    f.write(new_content)

