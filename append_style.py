with open("app/static/style.css", "a") as f:
    f.write("""
/* Login Specific Fixes */
.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--secondary);
}

.login-card {
  max-width: 900px;
  width: 100%;
  padding: 0;
  overflow: hidden;
}

.login-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.login-aside {
  background-color: var(--primary);
  color: var(--primary-foreground);
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-aside .sidebar-title {
  color: var(--primary-foreground);
  font-size: 1.875rem;
  margin-bottom: 0.5rem;
}

.login-aside .sidebar-subtitle {
  color: #94a3b8;
  font-size: 1rem;
  margin-bottom: 2rem;
}

.login-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.login-badge {
  background-color: rgba(255,255,255,0.1);
  color: var(--primary-foreground);
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  border: 1px solid rgba(255,255,255,0.2);
}

.login-form-wrap {
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background-color: var(--card);
}

.login-form-wrap button {
  margin-top: 1rem;
  width: 100%;
}

.login-form-wrap input {
  margin-bottom: 0.5rem;
}

.field-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--foreground);
}

.status-banner {
  margin-top: 1rem;
  font-size: 0.875rem;
  color: var(--muted-foreground);
  min-height: 1.25rem;
}
.status-banner.success { color: var(--success); }
.status-banner.error { color: var(--destructive); }

@media (max-width: 768px) {
  .login-grid {
    grid-template-columns: 1fr;
  }
}
""")
