with open("app/static/style.css", "a") as f:
    f.write("""
/* Fix generic layout issues */
.dashboard-layout {
  min-height: calc(100vh - 4rem);
}

.panel {
  border: 1px solid var(--border);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.stack > textarea, .stack > input {
  margin-bottom: 0.5rem;
}
""")
