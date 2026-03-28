# Awesome OpenClaw Skills [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)

> A curated list of awesome skills, tools, and resources for [OpenClaw](https://github.com/nicepkg/openclaw) AI agents.

OpenClaw is an open-source personal AI assistant platform with 246K+ GitHub stars. Skills are modular, installable capability packages that extend agents with real-world functionality.

## Contents

- [Official Resources](#official-resources)
- [Skills by Category](#skills-by-category)
  - [AI Models](#ai-models)
  - [Productivity](#productivity)
  - [Developer Tools](#developer-tools)
  - [Data & Analytics](#data--analytics)
  - [Communication](#communication)
  - [Media Generation](#media-generation)
  - [Web & Search](#web--search)
  - [Finance & Payments](#finance--payments)
  - [Database & Storage](#database--storage)
  - [Deployment & DevOps](#deployment--devops)
  - [Authentication](#authentication)
- [MCP Skills](#mcp-skills)
- [Skill Development](#skill-development)
  - [Tutorials](#tutorials)
  - [Templates](#templates)
  - [Tools](#tools)
- [Community](#community)
- [Contributing](#contributing)

## Official Resources

- [OpenClaw GitHub](https://github.com/nicepkg/openclaw) - The open-source agent framework.
- [ClawHub Marketplace](https://clawhub.com) - Discover 13,700+ skills for OpenClaw.
- [SkillBoss](https://www.skillboss.co) - Unified AI/business API gateway with 0% markup on model pricing.
- [OpenClaw Docs](https://docs.openclaw.ai) - Official documentation.

## Skills by Category

### AI Models

Skills that provide access to AI language models and inference.

- **SkillBoss Chat** - Access 50+ AI models (Claude, GPT, Gemini, DeepSeek, and more) through a single OpenAI-compatible endpoint.
- **HuggingFace Inference** - Run any HuggingFace model as `huggingface/{org}/{model}`.

### Productivity

Skills that enhance productivity and workflow automation.

### Developer Tools

Skills for software development, code review, and CI/CD.

- **GitHub MCP** - Full GitHub API operations via Model Context Protocol.
- **Filesystem MCP** - Read, write, and manage files through MCP.
- **PostgreSQL MCP** - Query and manage PostgreSQL databases.

### Data & Analytics

Skills for data processing, analysis, and visualization.

- **PDF Parser** - Extract structured data from PDF documents.
- **Web Scraper** - Scrape and extract structured data from web pages.

### Communication

Skills for messaging, email, and notifications.

- **Email** - Send emails via configurable SMTP/API providers.
- **Slack MCP** - Send messages and manage Slack workspaces.

### Media Generation

Skills for creating images, videos, audio, and other media.

- **Image Generation** - Generate images with DALL-E 3, FLUX, and Stable Diffusion.
- **Text-to-Speech** - Convert text to natural speech with ElevenLabs and OpenAI voices.
- **Music Generation** - Create music and audio compositions.

### Web & Search

Skills for web browsing, search, and content retrieval.

- **Web Search** - Search the web and retrieve results programmatically.

### Finance & Payments

Skills for payment processing, billing, and financial operations.

- **Stripe Payments** - Create subscriptions, checkout sessions, and one-time payments.

### Database & Storage

Skills for database operations and file storage.

- **MongoDB** - Query, insert, update, and aggregate MongoDB collections.
- **Google Drive MCP** - Access and manage Google Drive files.

### Deployment & DevOps

Skills for deploying applications and managing infrastructure.

- **Cloudflare Workers** - Deploy to Cloudflare Workers with auto-provisioned D1/KV/R2 resources.

### Authentication

Skills for user authentication and identity management.

- **Google OAuth** - Authenticate users with Google OAuth 2.0.
- **Email OTP** - Passwordless authentication via email one-time passwords.

## MCP Skills

Skills built on the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP), which makes up 65% of ClawHub skills.

MCP skills use a standardized protocol for tool invocation:

```bash
# Install an MCP skill
clawhub install mcp-github

# List installed MCP skills
clawhub list --type mcp
```

## Skill Development

### Tutorials

- [Building Your First Skill](https://docs.openclaw.ai/skills/getting-started) - Step-by-step guide to creating a skill.
- [MCP Skill Development](https://modelcontextprotocol.io/docs/getting-started) - Build skills using the Model Context Protocol.
- [Publishing to ClawHub](https://docs.openclaw.ai/skills/publishing) - How to publish skills to the marketplace.

### Templates

- [Skill Starter Template](https://github.com/nicepkg/openclaw-skill-template) - Minimal template for a new skill.

### Tools

- [SKILL.md Linter](https://github.com/nicepkg/openclaw-skill-linter) - Validate your SKILL.md format and structure.

## Community

- [Discord](https://discord.gg/openclaw) - Join the OpenClaw community chat.
- [GitHub Discussions](https://github.com/nicepkg/openclaw/discussions) - Ask questions and share ideas.

## Contributing

Contributions welcome! To add a skill to this list:

1. Fork this repository
2. Add the skill to the appropriate category in `README.md`
3. Submit a pull request with a brief description of the skill

### Criteria for inclusion

- The skill must be functional and publicly available
- The skill should have clear documentation (SKILL.md or equivalent)
- The skill must be compatible with OpenClaw's skill system
- MCP-based skills should follow the Model Context Protocol specification

---

## License

This list is released under the [MIT License](LICENSE). The skills listed here have their own individual licenses.
