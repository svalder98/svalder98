import json
import os
import urllib.request
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


def github_api(url: str):
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-updater"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_public_repos():
    repos = github_api(
        f"https://api.github.com/users/{USERNAME}/repos"
        f"?per_page=100&sort=pushed&direction=desc"
    )

    clean = []

    for repo in repos:
        if repo.get("fork"):
            continue

        if repo.get("name") == PROFILE_REPO:
            continue

        clean.append({
            "name": repo.get("name", ""),
            "url": repo.get("html_url", ""),
            "description": repo.get("description") or "Public engineering repository",
            "language": repo.get("language") or "Mixed",
            "topics": repo.get("topics") or [],
            "updated_at": repo.get("pushed_at") or repo.get("updated_at") or ""
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
        capabilities = data.get("capabilities", [])
        return [str(item) for item in capabilities if str(item).strip()]
    except Exception:
        return []


def build_auto_section():
    repos = fetch_public_repos()
    private_capabilities = load_private_capabilities()

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append(f"<sub>Last automatic update: {updated}</sub>")
    lines.append("")
    lines.append("<div align=\"center\">")
    lines.append("")
    lines.append("<table>")
    lines.append("  <tr>")
    lines.append("    <th>Public Repository</th>")
    lines.append("    <th>Detected Stack</th>")
    lines.append("    <th>Engineering Signal</th>")
    lines.append("  </tr>")

    for repo in repos:
        categories = " · ".join(classify_repo(repo))
        language = repo.get("language", "Mixed")
        description = repo.get("description", "Public engineering repository")

        if len(description) > 90:
            description = description[:87] + "..."

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

    if private_capabilities:
        lines.append("<div align=\"center\">")
        lines.append("")
        lines.append("<b>Sanitized private-project evidence</b>")
        lines.append("")
        lines.append("<br/><br/>")
        lines.append("")

        for capability in private_capabilities[:12]:
            safe = capability.replace("<", "").replace(">", "")
            badge_text = safe.replace(" ", "%20")
            lines.append(
                f"<img src=\"https://img.shields.io/badge/{badge_text}-0F172A?style=for-the-badge\" />"
            )

        lines.append("")
        lines.append("</div>")
        lines.append("")

    return "\n".join(lines)


def update_readme():
    if not README_PATH.exists():
        raise FileNotFoundError("README.md not found")

    readme = README_PATH.read_text(encoding="utf-8")
    auto_content = build_auto_section()

    replacement = f"{START_MARKER}\n{auto_content}\n{END_MARKER}"

    if START_MARKER not in readme or END_MARKER not in readme:
        readme += f"\n\n---\n\n## Auto-updated Engineering Signals\n\n{replacement}\n"
    else:
        before = readme.split(START_MARKER)[0]
        after = readme.split(END_MARKER)[1]
        readme = before + replacement + after

    README_PATH.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    update_readme()
