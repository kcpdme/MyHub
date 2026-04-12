import re
files = ["app/templates/index.html", "app/templates/login.html"]
for p in files:
    with open(p, "r") as f:
        t = f.read()
    t = re.sub(r'\?v=\w+', '?v=20260412e', t)
    with open(p, "w") as f:
        f.write(t)
