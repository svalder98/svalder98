import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

USERNAME = "svalder98"
PROFILE_REPO = "svalder98"

README_PATH = Path("README.md")
PRIVATE_EVIDENCE_PATH = Path("profile-data/private_evidence.json")

START_MARKER = "<!-- PROFILE-AUTO:START -->"
END_MARKER = "<!-- PROFILE-AUTO:END -->"

CATEGORY_KEYWORDS = {
    "AI Systems": [
        "ai", "llm", "agent", "openai", "claude", "gemini", "automation", "prompt"
    ],
    "Backend": [
        "python", "fastapi", "api", "backend", "postgresql", "sqlalchemy", "docker"
    ],
    "Frontend": [
        "react", "nextjs", "vite", "typescript", "tailwind", "frontend"
    ],
    "Web3": [
        "ethereum", "solidity", "web3", "defi", "uniswap", "blockchain"
    ],
    "Automation": [
        "bot", "telegram", "monitoring", "scraping", "pipeline", "workflow"
    ]
}

# Stack detectado por lenguaje via API (sin nombres de proyectos)
LANGUAGE_TO_STACK = {
    "Python":     "Python",
    "TypeScript": "TypeScript",
    "JavaScript": "JavaScript",
    "Solidity":   "Solidity · Web3",
    "Shell":      "Shell · DevOps",
    "Dockerfile": "Docker",
    "HTML":       "HTML · Frontend",
    "CSS":        "CSS · Frontend",
    "Go":         "Go",
    "Rust":       "Rust",
    "SQL":        "SQL · Database",
}


def github_api(url: str, token: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater",
        "Authorization": f"Bearer {token}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None


def fetch_all_repos(token: str):
    """Obtiene TODOS los repos (públicos + privados) via GH_PAT."""
    page = 1
    repos = []
    while True:
        url = (
            f"https://api.github.com/user/repos"
            f"?per_page=100&page={page}&sort=pushed&direction=desc"
        )
        batch = github_api(url, token)
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def aggregate_languages(repos: list, token: str) -> dict:
    """
    Suma bytes por lenguaje en todos los repos.
    NUNCA expone nombres de repos privados.
    """
    totals = {}
    for repo in repos:
        if repo.get("name") == PROFILE_REPO:
            continue
        if repo.get("fork"):
            continue
        owner = repo.get("owner", {}).get("login", "")
        name = repo.get("name", "")
        url = f"https://api.github.com/repos/{owner}/{name}/languages"
        langs = github_api(url, token)
        if not langs:
            continue
        for lang, count in langs.items():
            totals[lang] = totals.get(lang, 0) + count
    return totals


def build_stack_badges(lang_totals: dict) -> list:
    """Convierte bytes por lenguaje en badges sin mencionar proyectos."""
    total_bytes = sum(lang_totals.values()) or 1
    badges = []
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
    for lang, count in sorted_langs[:10]:
        pct = round((count / total_bytes) * 100, 1)
        label = LANGUAGE_TO_STACK.get(lang, lang)
        badge_text = f"{label}%20{pct}%25".replace(" ", "%20")
        badges.append(
            f'<img src="https://img.shields.io/badge/{badge_text}-0F172A'
            f'?style=for-the-badge" />'
        )
    return badges


def fetch_public_repos(token: str):
    repos = github_api(
        f"https://api.github.com/users/{USERNAME}/repos"
        f"?per_page=100&sort=pushed&direction=desc",
        token
    )
    clean = []
    for repo in (repos or []):
        if repo.get("fork") or repo.get("name") == PROFILE_REPO:
            continue
        if repo.get("private"):
            continue
        clean.append({
            "name": repo.get("name", ""),
            "url": repo.get("html_url", ""),
            "description": repo.get("description") or "Public engineering repository",
            "language": repo.get("language") or "Mixed",
            "topics": repo.get("topics") or [],
        })
    return clean[:8]


def classify_repo(repo):
    text = " ".join([
        repo.get("name", ""),
        repo.get("description", ""),
        repo.get("language", ""),
        " ".join(repo.get("topics", []))
    ]).lower()
    matched = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.append(category)
    return matched[:3] if matched else ["Software Engineering"]


def load_private_capabilities():
    if not PRIVATE_EVIDENCE_PATH.exists():
        return []
    try:
        data = json.loads(PRIVATE_EVIDENCE_PATH.read_text(encoding="utf-8"))
        return [str(i) for i in data.get("capabilities", []) if str(i).strip()]
    except Exception:
        return []


def build_auto_section(token: str) -> str:
    public_repos = fetch_public_repos(token)
    all_repos = fetch_all_repos(token)
    lang_totals = aggregate_languages(all_repos, token)
    stack_badges = build_stack_badges(lang_totals)
    private_capabilities = load_private_capabilities()

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append(f"<sub>Last automatic update: {updated}</sub>")
    lines.append("")

    # --- Stack detectado de todos los repos (sin nombres privados) ---
    if stack_badges:
        lines.append("### Detected Stack (all repositories)")
        lines.append("")
        lines.append('<div align="center">')
        lines.append("")
        lines.extend(stack_badges)
        lines.append("")
        lines.append("</div>")
        lines.append("")

    # --- Tabla repos públicos ---
    if public_repos:
        lines.append("### Public Engineering Activity")
        lines.append("")
        lines.append('<div align="center">')
        lines.append("")
        lines.append("<table>")
        lines.append("  <tr>")
        lines.append("    <th>Repository</th>")
        lines.append("    <th>Stack</th>")
        lines.append("    <th>Signal</th>")
        lines.append("  </tr>")
        for repo in public_repos:
            categories = " · ".join(classify_repo(repo))
            language = repo.get("language", "Mixed")
            lines.append("  <tr>")
            lines.append(
                f"    <td><a href=\"{repo['url']}\"><b>{repo['name']}</b></a></td>"
            )
            lines.append(f"    <td>{language}</td>")
            lines.append(f"    <td>{categories}</td>")
            lines.append("  </tr>")
        lines.append("</table>")
        lines.append("")
        lines.append("</div>")
        lines.append("")

    # --- Capabilities privadas (manual, sin context de proyecto) ---
    if private_capabilities:
        lines.append("### Private-Project Capabilities")
        lines.append("")
        lines.append('<div align="center">')
        lines.append("")
        for cap in private_capabilities[:12]:
            safe = cap.replace("<", "").replace(">", "")
            badge_text = safe.replace(" ", "%20")
            lines.append(
                f'<img src="https://img.shields.io/badge/{badge_text}'
                f'-0F172A?style=for-the-badge" />'
            )
        lines.append("")
        lines.append("</div>")
        lines.append("")

    return "\n".join(lines)


def update_readme():
    token = os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("No token found: set GH_PAT or GITHUB_TOKEN")

    if not README_PATH.exists():
        raise FileNotFoundError("README.md not found")

    readme = README_PATH.read_text(encoding="utf-8")
    auto_content = build_auto_section(token)
    replacement = f"{START_MARKER}\n{auto_content}\n{END_MARKER}"

    if START_MARKER not in readme or END_MARKER not in readme:
        readme += f"\n\n---\n\n## Auto-updated Engineering Signals\n\n{replacement}\n"
    else:
        before = readme.split(START_MARKER)[0]
        after = readme.split(END_MARKER)[1]
        readme = before + replacement + after

    README_PATH.write_text(readme, encoding="utf-8")
    print(f"README updated — {len(auto_content.splitlines())} lines injected")


if __name__ == "__main__":
    update_readme()
