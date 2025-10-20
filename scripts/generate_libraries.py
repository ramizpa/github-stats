import requests, re, os, json
from collections import Counter

# Change this to your GitHub username
GITHUB_USER = "ramizpa"

BRANCHES = ["main", "master"]
HEADERS = {"Accept": "application/vnd.github.v3+json"}
if os.getenv("GITHUB_TOKEN"):
    HEADERS["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"

NORMALIZE = {
    "torch": "PyTorch", "pytorch": "PyTorch",
    "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "numpy": "NumPy", "pandas": "Pandas",
    "matplotlib": "Matplotlib", "seaborn": "Seaborn",
    "sklearn": "scikit-learn", "scikit-learn": "scikit-learn",
    "streamlit": "Streamlit", "mlflow": "MLflow", "shap": "SHAP"
}

def gh(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def list_repos(user):
    repos, page = [], 1
    while True:
        data = gh(f"https://api.github.com/users/{user}/repos", {"per_page":100,"page":page})
        if not data: break
        repos.extend(data)
        if len(data) < 100: break
        page += 1
    return repos

def get_raw(user, repo, path):
    for br in BRANCHES:
        url = f"https://raw.githubusercontent.com/{user}/{repo}/{br}/{path}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.text
    return None

def parse_reqs(txt):
    libs = []
    for line in txt.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            libs.append(re.split(r"[<=>\[]", line)[0].lower())
    return libs

def parse_imports(txt):
    libs = []
    for line in txt.splitlines():
        m = re.match(r'^\s*(?:from\s+([A-Za-z0-9_]+)|import\s+([A-Za-z0-9_]+))', line)
        if m:
            libs.append((m.group(1) or m.group(2)).lower())
    return libs

def normalize(name):
    return NORMALIZE.get(name.lower(), name.capitalize())

def scan_repo(user, name):
    found = []
    content = get_raw(user, name, "requirements.txt")
    if content:
        found += parse_reqs(content)
    if not found:
        tree = gh(f"https://api.github.com/repos/{user}/{name}/git/trees/HEAD?recursive=1")
        if tree and "tree" in tree:
            for f in tree["tree"]:
                if f["path"].endswith(".py"):
                    t = get_raw(user, name, f["path"])
                    if t:
                        found += parse_imports(t)
                    if len(found) > 20: break
    return [normalize(f) for f in found]

repos = list_repos(GITHUB_USER)
count = Counter()
for r in repos:
    print("Scanning", r["name"])
    libs = set(scan_repo(GITHUB_USER, r["name"]))
    for l in libs:
        count[l] += 1

items = []
if count:
    total = sum(count.values())
    for lib, c in count.most_common():
        items.append({"name": lib, "value": round(c/total*100,2), "count": c})

os.makedirs("data", exist_ok=True)
with open("data/libraries.json","w") as f:
    json.dump(items, f, indent=2)
print("Done -> data/libraries.json")

