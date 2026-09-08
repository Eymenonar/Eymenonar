#!/usr/bin/env python3
"""Update the seven-column OSS contribution grid in a profile README."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request

START_MARKER = "<!-- CONTRIB-GRID:START -->"
END_MARKER = "<!-- CONTRIB-GRID:END -->"
GITHUB_API = "https://api.github.com"


def _repo_name_from_api_url(url: str) -> str:
    prefix = f"{GITHUB_API}/repos/"
    if not url.startswith(prefix):
        return ""
    return url[len(prefix) :]


def filter_qualifying_repositories(
    pull_requests: list[dict],
    repositories: dict[str, dict],
    username: str,
    min_stars: int,
) -> list[dict]:
    """Return unique external repositories meeting the star threshold."""
    qualifying: dict[str, dict] = {}
    for pull_request in pull_requests:
        full_name = _repo_name_from_api_url(pull_request.get("repository_url", ""))
        repository = repositories.get(full_name)
        if not repository or "/" not in full_name:
            continue
        owner = full_name.split("/", 1)[0]
        if owner.casefold() == username.casefold():
            continue
        if int(repository.get("stargazers_count", 0)) < min_stars:
            continue
        qualifying[full_name.casefold()] = repository
    return sorted(
        qualifying.values(),
        key=lambda repo: (-int(repo.get("stargazers_count", 0)), repo["full_name"].casefold()),
    )


def render_grid(repositories: list[dict], columns: int = 7) -> str:
    """Render repositories as a fixed-width HTML table."""
    if not repositories:
        return "_Henüz 1.000+ yıldızlı bir projede birleştirilmiş katkı yok._"

    cells = []
    for repository in repositories:
        full_name = repository["full_name"]
        url = repository["html_url"]
        stars = int(repository.get("stargazers_count", 0))
        cells.append(
            '<td align="center" width="14.28%">'
            f'<a href="{url}"><strong>{full_name}</strong></a><br>'
            f'⭐ {stars:,}'
            "</td>"
        )

    rows = []
    for offset in range(0, len(cells), columns):
        row = cells[offset : offset + columns]
        row.extend('<td width="14.28%"></td>' for _ in range(columns - len(row)))
        rows.append("<tr>\n" + "\n".join(row) + "\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def replace_generated_section(readme: str, generated: str) -> str:
    """Replace the content between contribution-grid markers."""
    if START_MARKER not in readme or END_MARKER not in readme:
        raise ValueError("README contribution-grid markers are missing")
    before, remainder = readme.split(START_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    return f"{before}{START_MARKER}\n{generated}\n{END_MARKER}{after}"


def github_get(path: str, token: str) -> dict:
    request = urllib.request.Request(
        f"{GITHUB_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "profile-contribution-grid",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_merged_pull_requests(username: str, token: str) -> list[dict]:
    query = urllib.parse.quote(f"is:pr is:merged author:{username}")
    page = 1
    results: list[dict] = []
    while True:
        payload = github_get(f"/search/issues?q={query}&per_page=100&page={page}", token)
        items = payload.get("items", [])
        results.extend(items)
        if len(items) < 100:
            return results
        page += 1


def build_grid(username: str, token: str, min_stars: int) -> str:
    pull_requests = fetch_merged_pull_requests(username, token)
    names = {
        _repo_name_from_api_url(item.get("repository_url", ""))
        for item in pull_requests
    }
    repositories = {
        name: github_get(f"/repos/{name}", token)
        for name in sorted(names)
        if name
    }
    qualifying = filter_qualifying_repositories(
        pull_requests, repositories, username, min_stars
    )
    return render_grid(qualifying, columns=7)


def main() -> int:
    username = os.environ.get("PROFILE_USERNAME", "Eymenonar")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GH_TOKEN or GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    min_stars = int(os.environ.get("MIN_STARS", "1000"))
    readme_path = Path(os.environ.get("README_PATH", "README.md"))
    updated = replace_generated_section(
        readme_path.read_text(), build_grid(username, token, min_stars)
    )
    readme_path.write_text(updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
