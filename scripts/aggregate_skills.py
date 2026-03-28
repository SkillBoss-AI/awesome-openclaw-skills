#!/usr/bin/env python3
"""
aggregate_skills.py — Merge data from all collection scripts and generate README.md.

Reads data/github_skills.json and data/awesome_list_skills.json,
deduplicates by repo URL, assigns categories, and generates the
awesome-list README.md.

Usage:
    python3 scripts/aggregate_skills.py
    python3 scripts/aggregate_skills.py --data-dir ./data --output ./README.md
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Category configuration
# ---------------------------------------------------------------------------

# Broader categories for the awesome-list, with keyword matching rules.
# Order matters: first match wins. More specific categories come BEFORE
# broad catch-all categories like "AI Models & Inference".
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    # --- Specific categories first (before broad AI catch-all) ---
    ("MCP Servers & Protocol", [
        "mcp server", "mcp-server", "model context protocol",
        "mcp tool", "mcp client", "mcp framework", "mcp ", "fastmcp",
        "mcp-", "-mcp",
    ]),
    ("Code & Developer Tools", [
        "code review", "github", "gitlab", "git ", "linter", "formatter",
        "ide", "vscode", "neovim", "cursor", "dev tool", "developer tool",
        "code gen", "code assist", "code search", "refactor", "debug",
        "compiler", "build tool",
        "ci/cd", "ci cd", "testing", "test runner", "unit test",
        "terminal", "shell", "cli tool", "sdk", "boilerplate",
        "figma", "user-agent", "parser-js",
    ]),
    ("Data & Analytics", [
        "database", "postgres", "mysql", "sqlite", "mongodb", "redis",
        "sql", "query", "analytics", "data pipeline", "etl", "dataframe",
        "pandas", "bigquery", "snowflake", "elasticsearch", "supabase",
        "data visual", "chart", "dashboard", "grafana", "toolbox for database",
    ]),
    ("Web & Search", [
        "web search", "browser", "scrape", "scraping", "crawl", "crawler",
        "search engine", "google search", "bing", "duckduckgo", "tavily",
        "brave search", "web fetch", "puppeteer",
        "playwright", "selenium", "chrome mcp", "chrome extension",
    ]),
    ("Media & Content Generation", [
        "image gen", "image creat", "dall-e", "flux", "stable diffusion",
        "midjourney", "video", "audio", "tts", "text-to-speech", "speech",
        "music", "voice", "podcast", "media gen", "svg", "diagram",
        "canvas", "drawing", "humanizer", "rewrite", "ai-generated writing",
    ]),
    ("File & Document Management", [
        "filesystem", "pdf", "csv", "excel",
        "notion", "confluence", "gdrive", "google drive",
        "dropbox", "s3 bucket", "upload", "download",
    ]),
    ("Communication & Messaging", [
        "slack", "discord", "telegram", "email", "smtp", "notification",
        "wechat", "webhook", "sms", "twilio",
    ]),
    ("Cloud & DevOps", [
        "aws", "azure", "gcp", "google cloud", "cloudflare", "vercel",
        "docker", "kubernetes", "terraform", "deploy", "serverless",
        "lambda", "cloud run", "ec2", "infrastructure", "sandbox",
        "e2b",
    ]),
    ("AI Agent Frameworks", [
        "agent framework", "ai agent", "langchain",
        "langgraph", "autogen", "crewai", "swarm", "orchestrat",
        "agentic", "multi-agent", "agent skill", "agent harness",
        "agent platform", "observability", "monitoring",
    ]),
    ("Productivity & Workflow", [
        "todo", "task", "calendar", "schedule", "workflow", "automat",
        "zapier", "n8n", "productivity", "project manage", "jira",
        "linear", "trello", "asana", "obsidian", "note",
        "google workspace", "marketing skill", "planning",
    ]),
    ("Security & Auth", [
        "security", "auth", "oauth", "jwt", "encrypt", "password",
        "secret", "vault", "certificate", "ssl", "tls", "firewall",
        "iam", "identity", "access management",
    ]),
    ("Finance & Payments", [
        "stripe", "payment", "billing", "invoice", "finance", "bank",
        "crypto", "bitcoin", "ethereum", "trading", "stock",
    ]),
    ("Knowledge & Memory", [
        "knowledge", "memory", "rag", "retrieval", "vector", "pinecone",
        "weaviate", "chroma", "qdrant", "embedding store", "knowledge base",
        "knowledge graph",
    ]),
    ("Maps & Location", [
        "map", "geolocation", "gps", "geocode", "weather", "location",
    ]),
    # --- Broad AI category last (catches remaining AI-related items) ---
    ("AI Models & Inference", [
        "llm", "openai", "anthropic", "inference", "ai model",
        "language model", "chat model", "embedding",
        "huggingface", "transformers", "mlx", "ollama",
    ]),
]

DEFAULT_CATEGORY = "Other"

# Name patterns that indicate a curated list / meta-resource (not a tool)
_AWESOME_LIST_PATTERNS = [
    "awesome-", "curated list", "curated collection",
    "system-prompts-and-models", "ai-guide", "资源大全",
    "everything-claude",
]

# Manual category overrides for well-known repos where auto-detection fails.
# Key: lowercase repo full_name (owner/repo), value: category.
MANUAL_OVERRIDES: dict[str, str] = {
    "langflow-ai/langflow": "AI Agent Frameworks",
    "lobehub/lobehub": "AI Agent Frameworks",
    "bytedance/deer-flow": "AI Agent Frameworks",
    "zhayujie/chatgpt-on-wechat": "Communication & Messaging",
    "tooljet/tooljet": "Code & Developer Tools",
    "danny-avila/librechat": "AI Models & Inference",
    "farion1231/cc-switch": "Code & Developer Tools",
    "composiohq/composio": "AI Agent Frameworks",
    "labring/fastgpt": "Knowledge & Memory",
    "googleworkspace/cli": "Productivity & Workflow",
    "yamadashy/repomix": "Code & Developer Tools",
    "oraios/serena": "Code & Developer Tools",
    "langchain-ai/deepagents": "AI Agent Frameworks",
    "othmanadi/planning-with-files": "Productivity & Workflow",
    "coreyhaines31/marketingskills": "Productivity & Workflow",
    "raga-ai-hub/ragaai-catalyst": "AI Agent Frameworks",
    "googleapis/genai-toolbox": "Data & Analytics",
    "casdoor/casdoor": "Security & Auth",
    "nevamind-ai/memu": "Knowledge & Memory",
    "creativetimofficial/ui": "Code & Developer Tools",
    "yusufkaraaslan/skill_seekers": "Code & Developer Tools",
    "hangwin/mcp-chrome": "Web & Search",
    "iofficeai/aionui": "Code & Developer Tools",
    "faisalman/ua-parser-js": "Code & Developer Tools",
}


def _categorize(name: str, description: str, topics: list[str] | None = None,
                full_name: str = "") -> str:
    """Assign category from name + description + topics."""
    # Check manual overrides first
    if full_name:
        override = MANUAL_OVERRIDES.get(full_name.lower())
        if override:
            return override

    text = f"{name} {description} {' '.join(topics or [])}".lower()

    # Detect curated lists / awesome-lists → always "Other"
    name_lower = name.lower()
    if any(p in name_lower for p in _AWESOME_LIST_PATTERNS):
        return DEFAULT_CATEGORY
    if "curated list" in text and ("skill" in text or "tool" in text or "resource" in text):
        return DEFAULT_CATEGORY

    for category, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return DEFAULT_CATEGORY


def _normalize_url(url: str) -> str:
    """Normalize a GitHub URL to canonical form for dedup."""
    url = url.rstrip("/").lower()
    url = re.sub(r"\.git$", "", url)
    # Remove trailing #readme or /tree/... or /blob/...
    url = re.sub(r"/(tree|blob)/.*$", "", url)
    return url


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_github_skills(path: Path) -> list[dict]:
    """Load and normalize github_skills.json."""
    if not path.exists():
        print(f"[WARN] {path} not found, skipping", file=sys.stderr)
        return []
    data = json.loads(path.read_text())
    repos = data.get("repos", [])
    result = []
    for r in repos:
        result.append({
            "name": r.get("name", "").split("/")[-1],  # Use short name
            "full_name": r.get("name", ""),
            "repo_url": r.get("repo_url", ""),
            "description": r.get("description", ""),
            "stars": r.get("stars", 0),
            "language": r.get("language", ""),
            "topics": r.get("topics", []),
            "source": "github-api",
        })
    return result


def load_awesome_list(path: Path) -> list[dict]:
    """Load and normalize awesome_list_skills.json."""
    if not path.exists():
        print(f"[WARN] {path} not found, skipping", file=sys.stderr)
        return []
    data = json.loads(path.read_text())
    entries = data.get("entries", [])
    result = []
    for e in entries:
        result.append({
            "name": e.get("name", ""),
            "full_name": "",
            "repo_url": e.get("repo_url", ""),
            "description": e.get("description", ""),
            "stars": 0,
            "language": "",
            "topics": [],
            "source": "awesome-list",
            "source_list": e.get("source_list", ""),
        })
    return result


# ---------------------------------------------------------------------------
# Merge & deduplicate
# ---------------------------------------------------------------------------

def merge_skills(github_skills: list[dict], awesome_skills: list[dict]) -> list[dict]:
    """Merge and deduplicate skills from all sources."""
    merged: dict[str, dict] = {}  # keyed by normalized URL

    # GitHub skills first (they have stars data)
    for s in github_skills:
        key = _normalize_url(s["repo_url"])
        if not key:
            continue
        merged[key] = s

    # Awesome list skills (fill in if not already present, or enrich)
    for s in awesome_skills:
        key = _normalize_url(s["repo_url"])
        if not key:
            continue
        if key not in merged:
            merged[key] = s
        else:
            # Enrich existing entry with awesome-list source info
            existing = merged[key]
            if not existing.get("description") and s.get("description"):
                existing["description"] = s["description"]
            existing.setdefault("source_list", "")
            if s.get("source_list"):
                if existing["source_list"]:
                    existing["source_list"] += ", " + s["source_list"]
                else:
                    existing["source_list"] = s["source_list"]

    # Assign categories
    for skill in merged.values():
        skill["category"] = _categorize(
            skill["name"],
            skill.get("description", ""),
            skill.get("topics", []),
            full_name=skill.get("full_name", ""),
        )

    # Sort by stars (descending), then by name
    result = sorted(
        merged.values(),
        key=lambda s: (-s.get("stars", 0), s.get("name", "").lower()),
    )

    return result


# ---------------------------------------------------------------------------
# README generation
# ---------------------------------------------------------------------------

def _format_stars(stars: int) -> str:
    """Format star count for display."""
    if stars >= 1000:
        return f"{stars / 1000:.1f}k"
    return str(stars)


def generate_readme(skills: list[dict], output_path: Path) -> dict:
    """Generate README.md from merged skills. Returns stats dict."""
    # Group by category
    categories: dict[str, list[dict]] = {}
    for s in skills:
        cat = s.get("category", DEFAULT_CATEGORY)
        categories.setdefault(cat, [])
        categories[cat].append(s)

    # Sort categories: by number of entries (descending), with Other last
    sorted_cats = sorted(
        categories.keys(),
        key=lambda c: (c == DEFAULT_CATEGORY, -len(categories[c])),
    )

    # Build README
    lines = []
    lines.append("# Awesome OpenClaw Skills [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)")
    lines.append("")
    lines.append("> A curated list of the best AI agent skills, tools, and MCP servers.")
    lines.append(f"> **{len(skills)} skills** across **{len(sorted_cats)} categories**. Updated daily.")
    lines.append(">")
    lines.append("> Powered by [SkillBoss](https://www.skillboss.co) — the unified AI/business API gateway.")
    lines.append("")

    # Table of contents
    lines.append("## Contents")
    lines.append("")
    for cat in sorted_cats:
        anchor = cat.lower().replace(" & ", "--").replace(" ", "-")
        lines.append(f"- [{cat}](#{anchor}) ({len(categories[cat])})")
    lines.append("- [Contributing](#contributing)")
    lines.append("- [License](#license)")
    lines.append("")

    # Top 20 by stars
    top_starred = [s for s in skills if s.get("stars", 0) > 0][:20]
    if top_starred:
        lines.append("## Top 20 by Stars")
        lines.append("")
        lines.append("| # | Name | Description | Stars |")
        lines.append("|---|------|-------------|-------|")
        for i, s in enumerate(top_starred, 1):
            name = s.get("full_name") or s.get("name", "")
            url = s.get("repo_url", "")
            desc = s.get("description", "")[:80].replace("|", "\\|")
            if len(s.get("description", "")) > 80:
                desc += "..."
            stars = _format_stars(s.get("stars", 0))
            lines.append(f"| {i} | [{name}]({url}) | {desc} | {stars} |")
        lines.append("")

    # Category sections
    for cat in sorted_cats:
        lines.append(f"## {cat}")
        lines.append("")
        entries = categories[cat]

        # If entries have stars, show as table sorted by stars
        has_stars = any(e.get("stars", 0) > 0 for e in entries)

        if has_stars:
            lines.append("| Name | Description | Stars |")
            lines.append("|------|-------------|-------|")
            for s in entries:
                name = s.get("full_name") or s.get("name", "")
                url = s.get("repo_url", "")
                desc = s.get("description", "")[:100].replace("|", "\\|")
                if len(s.get("description", "")) > 100:
                    desc += "..."
                stars_val = s.get("stars", 0)
                stars = _format_stars(stars_val) if stars_val > 0 else "-"
                lines.append(f"| [{name}]({url}) | {desc} | {stars} |")
        else:
            for s in entries:
                name = s.get("name", "")
                url = s.get("repo_url", "")
                desc = s.get("description", "")[:120]
                if len(s.get("description", "")) > 120:
                    desc += "..."
                lines.append(f"- [{name}]({url}) — {desc}")

        lines.append("")

    # Contributing section
    lines.append("## Contributing")
    lines.append("")
    lines.append("Contributions welcome! To add a skill:")
    lines.append("")
    lines.append("1. Fork this repository")
    lines.append("2. Add the skill to the appropriate category")
    lines.append("3. Submit a pull request with a brief description")
    lines.append("")
    lines.append("### Criteria")
    lines.append("")
    lines.append("- The project must be functional and publicly available")
    lines.append("- It should have clear documentation or a README")
    lines.append("- Preference for actively maintained projects (updated in last 6 months)")
    lines.append("")

    # License
    lines.append("## License")
    lines.append("")
    lines.append("This list is released under the [MIT License](LICENSE). Listed projects have their own licenses.")
    lines.append("")

    # Footer
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines.append("---")
    lines.append("")
    lines.append(f"*Last updated: {now}. Auto-generated by [SkillBoss](https://www.skillboss.co) Growth Agent.*")
    lines.append("")

    readme_text = "\n".join(lines)
    output_path.write_text(readme_text)

    stats = {
        "total_skills": len(skills),
        "total_categories": len(sorted_cats),
        "categories": {cat: len(categories[cat]) for cat in sorted_cats},
        "top_skill": skills[0]["name"] if skills else "",
        "generated_at": now,
    }

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Aggregate skills data and generate README.md")
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Directory containing data JSON files (default: ./data)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output README.md path (default: ./README.md)")
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    data_dir = Path(args.data_dir) if args.data_dir else repo_root / "data"
    output_path = Path(args.output) if args.output else repo_root / "README.md"

    print(f"[INFO] Data dir: {data_dir}", file=sys.stderr)
    print(f"[INFO] Output: {output_path}", file=sys.stderr)

    # Load data
    github_skills = load_github_skills(data_dir / "github_skills.json")
    print(f"[INFO] Loaded {len(github_skills)} GitHub skills", file=sys.stderr)

    awesome_skills = load_awesome_list(data_dir / "awesome_list_skills.json")
    print(f"[INFO] Loaded {len(awesome_skills)} awesome-list skills", file=sys.stderr)

    # Merge
    merged = merge_skills(github_skills, awesome_skills)
    print(f"[INFO] Merged total: {len(merged)} unique skills", file=sys.stderr)

    # Save merged data
    merged_path = data_dir / "merged_skills.json"
    merged_path.parent.mkdir(parents=True, exist_ok=True)
    merged_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_count": len(merged),
        "skills": merged,
    }
    merged_path.write_text(json.dumps(merged_data, indent=2, ensure_ascii=False))
    print(f"[INFO] Saved merged data to {merged_path}", file=sys.stderr)

    # Generate README
    stats = generate_readme(merged, output_path)
    print(f"[INFO] Generated README.md at {output_path}", file=sys.stderr)

    # Print summary
    print(f"\n=== Aggregation Summary ===")
    print(f"Total skills: {stats['total_skills']}")
    print(f"Categories: {stats['total_categories']}")
    for cat, count in stats["categories"].items():
        print(f"  {cat}: {count}")
    print(f"Generated at: {stats['generated_at']}")


if __name__ == "__main__":
    main()
