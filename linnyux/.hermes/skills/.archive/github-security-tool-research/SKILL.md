---
name: github-security-tool-research
description: Research and analyze open-source security tools on GitHub using REST API search, raw file fetching, and source code analysis. Covers FRP bypass, exploit tools, protocol implementations, and vulnerability research.
tags: [github, security, research, osint, tools]
---

# GitHub Security Tool Research

Systematically find, fetch, and analyze open-source security tools on GitHub using the REST API and raw file access.

## Workflow

### 1. Repository Discovery
Use GitHub REST API search to find relevant repositories:

```bash
# Basic search with stars sort
curl -s "https://api.github.com/search/repositories?q=QUERY&sort=stars&order=desc&per_page=15" | \
  python3 -c "import json,sys; data=json.load(sys.stdin); \
  [print(f'{r[\"full_name\"]} ⭐{r[\"stargazers_count\"]} | {r[\"description\"][:150] if r[\"description\"] else \"No desc\"}') \
  for r in data.get('items',[])]"
```

**Query design tips:**
- Use `+` for word separation, `%22` for quoted phrases
- Combine technical terms with `OR` for broader coverage: `term1+OR+term2`
- Include protocol names, vulnerability types, and device categories
- Sort by `stars` for quality signal, `updated` for freshness
- Try multiple query variations — single queries often miss relevant repos

### 2. Repository Metadata
Fetch detailed info about discovered repos:

```bash
curl -s "https://api.github.com/repos/OWNER/REPO" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); \
  print(f'Desc: {d.get(\"description\")}\nStars: {d.get(\"stargazers_count\")}\nLang: {d.get(\"language\")}\nUpdated: {d.get(\"updated_at\")}\nTopics: {d.get(\"topics\")}\nLicense: {d.get(\"license\",{}).get(\"name\",\"None\") if d.get(\"license\") else \"None\"}\nDefault branch: {d.get(\"default_branch\")}')"
```

### 3. File Listing
Discover repository structure:

```bash
curl -s "https://api.github.com/repos/OWNER/REPO/contents/" | \
  python3 -c "import json,sys; [print(f'{x[\"name\"]} ({x[\"type\"]})') for x in json.load(sys.stdin)]"
```

For subdirectories: append path to the URL (e.g., `/contents/subdir`).

### 4. Source File Fetching
Fetch actual source code for analysis:

**Primary method — raw.githubusercontent.com:**
```bash
curl -s "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/FILE" 2>/dev/null
```

**Fallback — GitHub API content endpoint (when raw returns 404):**
```bash
curl -s "https://api.github.com/repos/OWNER/REPO/contents/FILE" | \
  python3 -c "import json,sys,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode())"
```

**Branch fallback:** If `main` returns 404, try `master`:
1. First check default branch via API: `curl -s "https://api.github.com/repos/OWNER/REPO" | python3 -c "...d.get('default_branch')..."`
2. Then fetch with the correct branch name

### 5. Source Code Analysis
Read and analyze fetched source to understand:
- **Exploit chain:** What steps does the tool execute in sequence?
- **Protocol usage:** Which protocols/commands does it use?
- **Dependencies:** What libraries does it require?
- **Device compatibility:** Which devices/versions are supported?
- **Security patches:** When was the vulnerability patched?

### 6. Multi-Repo Comparison
Compare approaches across multiple tools:
- Identify common techniques (shared commands, same exploit paths)
- Note differences in implementation (language, platform, automation level)
- Assess which approach is most reliable or up-to-date

## Pitfalls

1. **Raw URL 404 errors:** `raw.githubusercontent.com` may return 404 if the default branch isn't `main`. Always check via API first or try both `main` and `master`.

2. **GitHub code search requires auth:** The `/search/code` endpoint often returns empty results without authentication. Use `/search/repositories` instead for discovery.

3. **API rate limits:** Unauthenticated GitHub API requests are limited to 60/hour. For heavy research, use `gh` CLI with auth or add delays between requests.

4. **Repository descriptions may be outdated:** A tool's README may claim support for older devices only, but the source code might work on newer ones. Always read the actual code.

5. **Fork chains:** Many security tools are forks of forks. Check the original repo and follow the fork chain to find the most maintained version.

## Example: Samsung FRP Bypass Research

For a concrete example of this workflow applied to mobile security research, see `references/samsung-frp-bypass-findings.md`.
