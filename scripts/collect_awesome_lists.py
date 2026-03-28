#!/usr/bin/env python3
"""
collect_awesome_lists.py — Scrape known awesome-list repos for skill/tool entries.

Fetches README.md from hardcoded awesome-list repositories via the GitHub API,
parses markdown list entries (e.g. "- [name](url) - description"), and outputs
deduplicated JSON to data/awesome_list_skills.json.

Usage:
    python3 scripts/collect_awesome_lists.py
    python3 scripts/collect_awesome_lists.py --output /tmp/test.json
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Hardcoded awesome-list repos to scrape
AWESOME_REPOS: list[dict] = [
    {
        "repo": "ComposioHQ/awesome-claude-skills",
        "label": "composio-awesome-claude-skills",
    },
    {
        "repo": "hesreallyhim/awesome-claude-code",
        "label": "awesome-claude-code",
    },
    {
        "repo": "travisvn/awesome-claude-skills",
        "label": "travisvn-awesome-claude-skills",
    },
    {
        "repo": "wong2/awesome-mcp-servers",
        "label": "awesome-mcp-servers",
    },
    {
        "repo": "punkpeye/awesome-ai-tools",
        "label": "awesome-ai-tools",
    },
    {
        "repo": "VoltAgent/awesome-agent-skills",
        "label": "awesome-agent-skills",
    },
    {
        "repo": "appcypher/awesome-mcp-servers",
        "label": "appcypher-awesome-mcp-servers",
    },
    {
        "repo": "sickn33/antigravity-awesome-skills",
        "label": "antigravity-awesome-skills",
    },
]

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "awesome_list_skills.json"

# Regex: matches markdown list items like:
#   - [Name](https://url) - Description
#   - **[Name](https://url)** - Description
#   - [Name](https://url) by [Author](url) - Description
# Captures: name, url, rest-of-line (description)
ENTRY_PATTERN = re.compile(
    r"^[-*]\s+"               # list bullet (- or *)
    r"\*{0,2}"                # optional bold **
    r"\[([^\]]+)\]"           # [Name]
    r"\(([^)]+)\)"            # (url)
    r"\*{0,2}"                # optional closing bold **
    r"\s*[-–—:]?\s*"          # separator (dash, colon, or space)
    r"(.+)$",                 # description (rest of line)
    re.MULTILINE,
)

# Filter: only keep entries whose URL points to a code/tool host
TOOL_URL_HOSTS = (
    "github.com",
    "gitlab.com",
    "npmjs.com",
    "pypi.org",
    "huggingface.co",
    "crates.io",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_github_token() -> str:
    """Resolve GitHub token from env, gh CLI config, or .env file."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    # Try gh CLI config (YAML)
    gh_config = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_config.exists():
        try:
            import yaml  # noqa: might not be available
            data = yaml.safe_load(gh_config.read_text())
            token = data.get("github.com", {}).get("oauth_token")
            if token:
                return token
        except Exception:
            # Fallback: simple text parsing for oauth_token line
            try:
                for line in gh_config.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("oauth_token:"):
                        token = line.split(":", 1)[1].strip()
                        if token:
                            return token
            except Exception:
                pass

    # Try /opt/agent/.env
    env_path = "/opt/agent/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k == "GITHUB_TOKEN" and v:
                    return v

    print("[ERROR] No GitHub token found. Set GITHUB_TOKEN or authenticate with gh CLI.", file=sys.stderr)
    sys.exit(1)


def _fetch_readme(token: str, repo: str) -> str | None:
    """Fetch and decode the README.md content from a GitHub repo via the API."""
    url = f"https://api.github.com/repos/{repo}/readme"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CloudAgent-AwesomeListCollector/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [WARN] HTTP {e.code} fetching {repo}/readme: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  [WARN] Failed to fetch {repo}/readme: {e}", file=sys.stderr)
        return None

    content_b64 = data.get("content", "")
    if not content_b64:
        print(f"  [WARN] Empty content for {repo}/readme", file=sys.stderr)
        return None

    try:
        return base64.b64decode(content_b64).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] Failed to decode {repo}/readme: {e}", file=sys.stderr)
        return None


def _is_tool_url(url: str) -> bool:
    """Check if a URL points to a known code/tool hosting platform."""
    url_lower = url.lower()
    return any(host in url_lower for host in TOOL_URL_HOSTS)


def _extract_repo_url(url: str) -> str | None:
    """Extract a canonical repo URL (e.g. github.com/owner/repo) from a possibly deeper link."""
    m = re.search(r"(https?://github\.com/[\w.\-]+/[\w.\-]+)", url)
    if m:
        return m.group(1).rstrip("/")
    # For non-GitHub hosts, return URL as-is if it's a tool host
    if _is_tool_url(url):
        return url.rstrip("/")
    return None


def _clean_description(desc: str) -> str:
    """Clean up extracted description text."""
    # Remove markdown links: [text](url) -> text
    desc = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", desc)
    # Remove bold/italic markers
    desc = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", desc)
    # Remove inline code
    desc = re.sub(r"`([^`]+)`", r"\1", desc)
    # Strip "by @author" attribution at end (with markdown link)
    desc = re.sub(r"\s*\*?By \[@?\w+\]\([^)]*\)\*?\s*$", "", desc, flags=re.IGNORECASE)
    # Strip "by author -" attribution at start (plain text, from awesome-claude-code format)
    desc = re.sub(r"^by\s+[\w\-]+\s*[-–—]\s*", "", desc, flags=re.IGNORECASE)
    # Collapse whitespace
    desc = re.sub(r"\s+", " ", desc).strip()
    # Truncate if too long
    if len(desc) > 300:
        desc = desc[:297] + "..."
    return desc


def _parse_entries(readme_text: str, source_label: str) -> list[dict]:
    """Parse markdown list entries from a README and return structured entries."""
    entries = []
    for match in ENTRY_PATTERN.finditer(readme_text):
        name = match.group(1).strip()
        raw_url = match.group(2).strip()
        raw_desc = match.group(3).strip()

        # Resolve URL to a canonical repo/tool URL
        repo_url = _extract_repo_url(raw_url)
        if not repo_url:
            continue

        description = _clean_description(raw_desc)
        if not description:
            continue

        entries.append({
            "name": name,
            "repo_url": repo_url,
            "description": description,
            "source": "awesome-list",
            "source_list": source_label,
        })

    return entries


# ---------------------------------------------------------------------------
# Main collection logic
# ---------------------------------------------------------------------------


def collect() -> list[dict]:
    """Fetch all awesome-list READMEs and extract unique skill/tool entries."""
    token = _resolve_github_token()

    all_entries: dict[str, dict] = {}  # keyed by repo_url for dedup

    for repo_info in AWESOME_REPOS:
        repo = repo_info["repo"]
        label = repo_info["label"]
        print(f"[INFO] Fetching {repo} ...", file=sys.stderr)

        readme = _fetch_readme(token, repo)
        if readme is None:
            print(f"  [WARN] Skipping {repo} (could not fetch README)", file=sys.stderr)
            continue

        entries = _parse_entries(readme, label)
        print(f"  [INFO] Parsed {len(entries)} entries from {repo}", file=sys.stderr)

        for entry in entries:
            key = entry["repo_url"].lower()
            if key not in all_entries:
                all_entries[key] = entry
            else:
                # If already seen, append source_list if different
                existing = all_entries[key]
                existing_sources = existing["source_list"]
                if label not in existing_sources:
                    existing["source_list"] = f"{existing_sources}, {label}"

    sorted_entries = sorted(all_entries.values(), key=lambda e: e["name"].lower())

    print(f"[INFO] Total unique entries collected: {len(sorted_entries)}", file=sys.stderr)
    return sorted_entries


def main():
    parser = argparse.ArgumentParser(description="Collect skills/tools from awesome-list repos")
    parser.add_argument("--output", "-o", type=str, default=str(DEFAULT_OUTPUT),
                        help="Output JSON file path")
    args = parser.parse_args()

    entries = collect()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(entries),
        "source_repos": [r["repo"] for r in AWESOME_REPOS],
        "entries": entries,
    }

    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    print(f"[INFO] Saved {len(entries)} entries to {output_path}", file=sys.stderr)

    # Summary to stdout
    sources: dict[str, int] = {}
    for e in entries:
        for s in e["source_list"].split(", "):
            sources[s] = sources.get(s, 0) + 1

    print(f"\nTotal: {len(entries)} unique entries")
    print("By source list:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")
    print(f"\nSample entries:")
    for e in entries[:5]:
        print(f"  {e['name']}: {e['description'][:60]}...")


if __name__ == "__main__":
    main()
