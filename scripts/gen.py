"""Render a github-readme-stats style card that also counts private repos.

The public github-readme-stats instance only sees public activity, so this
script queries the GraphQL API with your own token and draws the same card.

Usage:
  GH_TOKEN=... python scripts/gen.py            # fetch from the GraphQL API
  ./scripts/refresh.sh                          # fetch with your gh login, commit and push
  python scripts/gen.py --data sample.json      # render from a saved response
"""
import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

# octicons (16px)
ICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z",
    "commits": "M1.643 3.143.427 1.927A.25.25 0 0 0 0 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 0 0 .177-.427L2.715 4.215a6.5 6.5 0 1 1-1.18 4.458.75.75 0 1 0-1.493.154 8.001 8.001 0 1 0 1.6-5.684ZM7.75 4a.75.75 0 0 1 .75.75v2.992l2.028.812a.75.75 0 0 1-.557 1.392l-2.5-1A.751.751 0 0 1 7 8.25v-3.5A.75.75 0 0 1 7.75 4Z",
    "prs": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "issues": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3ZM8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "lock": "M4 4a4 4 0 0 1 8 0v2h.25c.966 0 1.75.784 1.75 1.75v5.5A1.75 1.75 0 0 1 12.25 15h-8.5A1.75 1.75 0 0 1 2 13.25v-5.5C2 6.784 2.784 6 3.75 6H4Zm8.25 3.5h-8.5a.25.25 0 0 0-.25.25v5.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-5.5a.25.25 0 0 0-.25-.25ZM10.5 6V4a2.5 2.5 0 1 0-5 0v2Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
}


def fetch():
    query = (ROOT / "scripts" / "query.graphql").read_text()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {os.environ['GH_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def summarize(raw):
    v = raw["data"]["viewer"]
    cc = v["contributionsCollection"]
    repos = v["repositories"]["nodes"]
    return {
        "name": v["name"] or v["login"],
        "stars": sum(r["stargazerCount"] for r in repos),
        # private contributions only come back as one total, so they are added to commits
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": v["pullRequests"]["totalCount"],
        "issues": v["issues"]["totalCount"],
        "private": sum(r["isPrivate"] for r in repos),
        "contributed": v["repositoriesContributedTo"]["totalCount"],
        "followers": v["followers"]["totalCount"],
    }


def rank(s):
    """Same formula as github-readme-stats (src/calculateRank.js)."""
    exp_cdf = lambda x: 1 - 2 ** -x
    log_cdf = lambda x: x / (1 + x)
    parts = [
        (2, exp_cdf(s["commits"] / 250)),
        (3, exp_cdf(s["prs"] / 50)),
        (1, exp_cdf(s["issues"] / 25)),
        (1, exp_cdf(0 / 2)),  # reviews
        (4, log_cdf(s["stars"] / 50)),
        (1, log_cdf(s["followers"] / 10)),
    ]
    pct = 100 * (1 - sum(w * v for w, v in parts) / sum(w for w, _ in parts))
    for t, level in zip([1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100], ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]):
        if pct <= t:
            return level, pct
    return "C", pct


def card(s):
    level, pct = rank(s)
    rows = [
        ("star", "Total Stars Earned:", s["stars"]),
        ("commits", "Total Commits (last year):", s["commits"]),
        ("prs", "Total PRs:", s["prs"]),
        ("issues", "Total Issues:", s["issues"]),
        ("lock", "Private Repositories:", s["private"]),
        ("repo", "Contributed to (last year):", s["contributed"]),
    ]
    H = 70 + 25 * len(rows)
    body = []
    for i, (icon, label, value) in enumerate(rows):
        body.append(
            f'<g transform="translate(25, {55 + i * 25 + 12.5})"><g class="stagger" style="animation-delay:{450 + i * 150}ms">'
            f'<svg class="icon" viewBox="0 0 16 16" width="16" height="16" y="-12.5"><path d="{ICONS[icon]}"/></svg>'
            f'<text class="stat" x="25">{label}</text><text class="stat" x="219.01">{value:,}</text></g></g>'
        )
    circ = 251.32741228718345  # 2πr, r=40
    offset = circ * (pct / 100)
    cy = 55 + 25 * len(rows) / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="467" height="{H}" viewBox="0 0 467 {H}" fill="none" role="img" aria-labelledby="titleId">
<title id="titleId">{escape(s["name"])}'s GitHub Stats, Rank: {level}</title>
<style>
.header{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:#2f80ed;animation:fadeInAnimation .8s ease-in-out forwards}}
.stat{{font:600 14px 'Segoe UI',Ubuntu,"Helvetica Neue",Sans-Serif;fill:#434d58}}
.stagger{{opacity:0;animation:fadeInAnimation .3s ease-in-out forwards}}
.rank-text{{font:800 24px 'Segoe UI',Ubuntu,Sans-Serif;fill:#434d58}}
.icon{{fill:#4c71f2}}
.rim{{stroke:#2f80ed;fill:none;stroke-width:6;opacity:.2}}
.ring{{stroke:#2f80ed;stroke-dasharray:{circ:.2f};stroke-dashoffset:{offset:.2f};fill:none;stroke-width:6;stroke-linecap:round;opacity:.8;animation:rankAnimation 1s ease-in-out}}
@keyframes rankAnimation{{from{{stroke-dashoffset:{circ:.2f}}}to{{stroke-dashoffset:{offset:.2f}}}}}
@keyframes fadeInAnimation{{from{{opacity:0}}to{{opacity:1}}}}
</style>
<rect x="0.5" y="0.5" rx="4.5" width="466" height="{H - 1}" stroke="#e4e2e2" fill="#fffefe"/>
<text x="25" y="35" class="header">{escape(s["name"])}'s GitHub Stats</text>
<circle class="rim" cx="380" cy="{cy}" r="40"/>
<circle class="ring" cx="380" cy="{cy}" r="40" transform="rotate(-90 380 {cy})"/>
<text x="380" y="{cy}" class="rank-text" text-anchor="middle" dominant-baseline="central">{level}</text>
{''.join(body)}
</svg>"""


def main():
    raw = json.load(open(sys.argv[sys.argv.index("--data") + 1])) if "--data" in sys.argv else fetch()
    s = summarize(raw)
    OUT.mkdir(exist_ok=True)
    (OUT / "stats.svg").write_text(card(s), encoding="utf-8")
    print("rank", rank(s), s)


if __name__ == "__main__":
    main()
