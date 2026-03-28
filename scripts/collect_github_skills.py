#!/usr/bin/env python3
"""
collect_github_skills.py — GitHub API data collection for skills/MCP repos.

Searches GitHub for Claude Code skills, MCP servers, and AI agent tools.
Outputs deduplicated JSON to data/github_skills.json.

Usage:
    python3 scripts/collect_github_skills.py
    python3 scripts/collect_github_skills.py --output /tmp/test.json
    python3 scripts/collect_github_skills.py --min-stars 50
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

from github import Auth, Github, GithubException, RateLimitExceededException

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SEARCH_QUERIES = [
    "claude code skills",
    "mcp server",
    "ai agent tools",
    "model context protocol",
    "claude mcp",
]

# Map keywords found in repo name/description/topics to a category
CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["mcp", "model context protocol"], "mcp-server"),
    (["claude code", "claude skill"], "claude-code-skill"),
    (["agent tool", "ai agent", "ai tool"], "ai-agent-tool"),
    (["llm tool", "langchain tool", "langgraph"], "llm-tool"),
]

DEFAULT_CATEGORY = "other"

SIX_MONTHS_AGO = datetime.now(timezone.utc) - timedelta(days=180)

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "github_skills.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_github_token() -> str:
    """Resolve GitHub token from env or gh CLI config."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    # Try gh CLI config
    gh_config = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_config.exists():
        try:
            data = yaml.safe_load(gh_config.read_text())
            token = data.get("github.com", {}).get("oauth_token")
            if token:
                return token
        except Exception:
            pass

    print("[ERROR] No GitHub token found. Set GITHUB_TOKEN or authenticate with gh CLI.", file=sys.stderr)
    sys.exit(1)


def _categorize(name: str, description: str, topics: list[str]) -> str:
    """Assign a category based on repo metadata."""
    text = f"{name} {description} {' '.join(topics)}".lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return DEFAULT_CATEGORY


def _search_repos(gh: Github, query: str, min_stars: int) -> list[dict]:
    """Run a single GitHub search query and return matching repos."""
    results = []
    full_query = f"{query} stars:>={min_stars}"

    try:
        repos = gh.search_repositories(query=full_query, sort="stars", order="desc")
    except RateLimitExceededException:
        print(f"[WARN] Rate limited on query: {query}", file=sys.stderr)
        return results
    except GithubException as e:
        print(f"[WARN] GitHub API error on query '{query}': {e}", file=sys.stderr)
        return results

    # GitHub search API returns up to 1000 results; we cap at 100 per query
    count = 0
    for repo in repos:
        if count >= 100:
            break
        count += 1

        # Filter: must have been pushed in the last 6 months
        if repo.pushed_at and repo.pushed_at < SIX_MONTHS_AGO:
            continue

        # Skip archived/disabled repos
        if repo.archived or repo.disabled:
            continue

        topics = []
        try:
            topics = repo.get_topics()
        except GithubException:
            pass

        results.append({
            "name": repo.full_name,
            "repo_url": repo.html_url,
            "description": (repo.description or "").strip(),
            "stars": repo.stargazers_count,
            "language": repo.language or "",
            "topics": topics,
            "last_pushed": repo.pushed_at.isoformat() if repo.pushed_at else "",
            "category": _categorize(repo.name, repo.description or "", topics),
        })

    return results


def collect(min_stars: int = 5) -> list[dict]:
    """Run all search queries and return deduplicated results sorted by stars."""
    token = _resolve_github_token()
    gh = Github(auth=Auth.Token(token), per_page=100)

    all_repos: dict[str, dict] = {}  # keyed by full_name to deduplicate

    for query in SEARCH_QUERIES:
        print(f"[INFO] Searching: {query}", file=sys.stderr)
        results = _search_repos(gh, query, min_stars)
        for repo in results:
            key = repo["name"]
            # Keep the entry with more stars if duplicate
            if key not in all_repos or repo["stars"] > all_repos[key]["stars"]:
                all_repos[key] = repo

    # Sort by stars descending
    sorted_repos = sorted(all_repos.values(), key=lambda r: r["stars"], reverse=True)

    print(f"[INFO] Total unique repos collected: {len(sorted_repos)}", file=sys.stderr)
    return sorted_repos


def main():
    parser = argparse.ArgumentParser(description="Collect GitHub skills/MCP repos")
    parser.add_argument("--output", "-o", type=str, default=str(DEFAULT_OUTPUT),
                        help="Output JSON file path")
    parser.add_argument("--min-stars", type=int, default=5,
                        help="Minimum stars filter (default: 5)")
    args = parser.parse_args()

    repos = collect(min_stars=args.min_stars)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(repos),
        "search_queries": SEARCH_QUERIES,
        "min_stars": args.min_stars,
        "repos": repos,
    }

    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    print(f"[INFO] Saved {len(repos)} repos to {output_path}", file=sys.stderr)

    # Print summary to stdout
    categories = {}
    for r in repos:
        cat = r["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nTotal: {len(repos)} repos")
    print("Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nTop 5 by stars:")
    for r in repos[:5]:
        print(f"  {r['stars']:>6} ★  {r['name']}: {r['description'][:60]}")


if __name__ == "__main__":
    main()
