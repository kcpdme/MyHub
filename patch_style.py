with open("app/static/style.css", "w") as f:
    f.write("""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --background: #f8fafc;
  --foreground: #0f172a;
  --card: #ffffff;
  --card-foreground: #0f172a;
  --popover: #ffffff;
  --popover-foreground: #0f172a;
  --primary: #0f172a;
  --primary-foreground: #f8fafc;
  --secondary: #f1f5f9;
  --secondary-foreground: #0f172a;
  --muted: #f1f5f9;
  --muted-foreground: #64748b;
  --accent: #f1f5f9;
  --accent-foreground: #0f172a;
  --destructive: #ef4444;
  --destructive-foreground: #f8fafc;
  --border: #e2e8f0;
  --input: #e2e8f0;
  --ring: #94a3b8;
  --radius: 0.75rem;
  
  --success: #10b981;
  --success-foreground: #ffffff;
}

* {
  box-sizing: border-box;
  border-color: var(--border);
}

body {
  margin: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--foreground);
  background-color: var(--background);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  letter-spacing: -0.025em;
  color: var(--foreground);
  margin-top: 0;
}

.app-shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.dashboard-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 2rem;
  align-items: start;
}

.panel {
  background-color: var(--card);
  color: var(--card-foreground);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.sidebar {
  position: sticky;
  top: 2rem;
  padding: 1.5rem 1rem;
}

.brand {
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: -0.025em;
  margin-bottom: 0.25rem;
}

.muted {
  color: var(--muted-foreground);
  font-size: 0.875rem;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 1.5rem;
}

button, input, select, textarea {
  font-family: inherit;
  font-size: 0.875rem;
  transition: all 0.15s ease;
}

button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  font-weight: 500;
  height: 2.5rem;
  padding: 0 1rem;
  background-color: var(--primary);
  color: var(--primary-foreground);
  border: 1px solid transparent;
  cursor: pointer;
  white-space: nowrap;
}

button:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

button:active {
  transform: translateY(0);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.nav-link {
  justify-content: flex-start;
  height: 2.25rem;
  padding: 0 0.75rem;
  background-color: transparent;
  color: var(--foreground);
  font-weight: 500;
}

.nav-link:hover {
  background-color: var(--secondary);
  color: var(--secondary-foreground);
  transform: none;
}

.nav-link.active {
  background-color: var(--secondary);
  color: var(--secondary-foreground);
  font-weight: 600;
}

.ghost {
  background-color: transparent;
  color: var(--foreground);
  border: 1px solid var(--input);
}

.ghost:hover {
  background-color: var(--accent);
  color: var(--accent-foreground);
}

input, select, textarea {
  display: flex;
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid var(--input);
  background-color: transparent;
  padding: 0.5rem 0.75rem;
  color: var(--foreground);
}

input:focus, select:focus, textarea:focus {
  outline: none;
  border-color: var(--ring);
  box-shadow: 0 0 0 1px var(--ring);
}

textarea {
  min-height: 80px;
  resize: vertical;
}

.main-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  background: transparent;
  box-shadow: none;
  border: none;
  border-bottom: 1px solid var(--border);
  border-radius: 0;
  margin-bottom: -0.5rem;
}

.topbar h1 {
  font-size: 1.5rem;
  margin: 0;
}

.menu-toggle {
  display: none;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: var(--secondary);
  color: var(--secondary-foreground);
  border: 1px solid var(--border);
}

.status-pill.success {
  background-color: rgba(16, 185, 129, 0.1);
  color: var(--success);
  border-color: rgba(16, 185, 129, 0.2);
}

.status-pill.error {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--destructive);
  border-color: rgba(239, 68, 68, 0.2);
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.row, .filter-row, .quick-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filter-row button, .quick-row button {
  flex: 1;
}

.list {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list li {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  background-color: var(--card);
  transition: box-shadow 0.2s ease;
}

.list li:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
}

.inbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0;
}

.inbox-grid li {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  background-color: var(--card);
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.inbox-grid li:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
}

.inbox-headline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.inbox-thumb {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
  background-color: var(--muted);
  border: 1px solid var(--border);
}

.inline-check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  cursor: pointer;
}

.inline-check input {
  width: auto;
  accent-color: var(--primary);
}

.done {
  text-decoration: line-through;
  color: var(--muted-foreground);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-item {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  background-color: var(--card);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.summary-item span {
  font-size: 0.875rem;
  color: var(--muted-foreground);
  font-weight: 500;
}

.summary-item strong {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.025em;
}

.toast-container {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  z-index: 50;
  pointer-events: none;
}

.toast {
  background-color: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  font-size: 0.875rem;
  font-weight: 500;
  min-width: 300px;
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toast::before {
  content: '';
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--primary);
}

.toast.success::before {
  background-color: var(--success);
}

.toast.error::before {
  background-color: var(--destructive);
}

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

.skeleton {
  background: linear-gradient(90deg, var(--muted) 25%, #e2e8f0 50%, var(--muted) 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 0.25rem;
  height: 1rem;
}

.skeleton.thumb {
  height: 200px;
  border-radius: 0.375rem;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 768px) {
  .app-shell {
    padding: 1rem;
  }
  
  .dashboard-layout {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px;
    z-index: 40;
    background-color: var(--background);
    border-right: 1px solid var(--border);
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    padding: 2rem 1.5rem;
  }
  
  .sidebar.open {
    transform: translateX(0);
    box-shadow: 10px 0 15px -3px rgba(0, 0, 0, 0.1);
  }
  
  .menu-toggle {
    display: inline-flex;
    padding: 0.5rem;
    height: auto;
    background-color: var(--secondary);
    color: var(--secondary-foreground);
    margin-right: 1rem;
  }
  
  .topbar {
    padding: 1rem 0;
    border-bottom: none;
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .topbar > div:first-child {
    display: flex;
    align-items: center;
    width: 100%;
  }
  
  .inbox-grid {
    grid-template-columns: 1fr;
  }
}
""")
