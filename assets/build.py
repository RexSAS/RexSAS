#!/usr/bin/env python3
"""Regenerates assets/terminal.svg and assets/stats.svg (needs the gh CLI, logged in).
Edit LINES, then run: python3 assets/build.py. A daily workflow reruns it to refresh the stats."""
import json
import subprocess
import time
from html import escape
from pathlib import Path

OUT = Path(__file__).parent / "terminal.svg"
BG, BAR, LINE = "#0f0e12", "#1a1920", "#2a2830"
INK, MUTED, ACCENT, SAND, SKY, GREEN = "#f2f1ed", "#8f8e88", "#e2492a", "#dcc47e", "#93b7cc", "#8fbf7f"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
PROMPT = "me@rxenv:~$ "

# (kind, text): "cmd" lines get typed out, everything else just appears
LINES = [
    ("cmd", "git clone git@github.com:me/side-projects.git"),
    ("out", "Cloning into 'side-projects'..."),
    ("out", "remote: Enumerating objects: way too many side projects, done."),
    ("warn", "warning: 3 projects are being rewritten from scratch. again."),
    ("cmd", "cd side-projects && make free-time"),
    ("err", "make: *** No rule to make target 'free-time'.  Stop."),
    ("cmd", "git commit -am \"fix: everything\""),
    ("out", "[main 0xfe] fix: everything"),
    ("out", " 1 file changed, 1 insertion(+), 4096 deletions(-)"),
]
COLORS = {"out": MUTED, "warn": SAND, "err": ACCENT}
W, LH, TOP, FS = 900, 26, 72, 16
H = TOP + LH * (len(LINES) + 1) + 8
CHAR = FS * 0.62  # generous monospace advance so the typing clip never cuts text


def build():
    parts, defs, t = [], [], 0.4
    for i, (kind, text) in enumerate(LINES):
        y = TOP + i * LH
        if kind == "cmd":
            dur = len(text) * 0.035
            x0 = 28 + len(PROMPT) * CHAR
            defs.append(f'<clipPath id="c{i}"><rect x="{x0}" y="{y - FS}" width="0" height="{LH}">'
                        f'<animate attributeName="width" from="0" to="{len(text) * CHAR + 10}" begin="{t:.2f}s" '
                        f'dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>')
            # prompt and command are separate <text>s because renderers ignore clip-path on a <tspan>
            parts.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
                         f'<text x="28" y="{y}" fill="{GREEN}">{escape(PROMPT)}</text>'
                         f'<text x="{x0}" y="{y}" fill="{INK}" clip-path="url(#c{i})">{escape(text)}</text></g>')
            t += dur + 0.5
        else:
            parts.append(f'<text x="28" y="{y}" fill="{COLORS[kind]}" opacity="0">{escape(text)}'
                         f'<set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/></text>')
            t += 0.35
    y = TOP + len(LINES) * LH
    parts.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t:.2f}s" fill="freeze"/>'
                 f'<text x="28" y="{y}" fill="{GREEN}">{escape(PROMPT)}</text>'
                 f'<rect x="{28 + len(PROMPT) * CHAR}" y="{y - FS + 2}" width="9" height="{FS + 2}" fill="{INK}">'
                 f'<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/></rect></g>')
    lights = "".join(f'<circle cx="{24 + k * 20}" cy="20" r="6" fill="{c}"/>'
                     for k, c in enumerate([ACCENT, SAND, GREEN]))
    alt = "Terminal: cloning side-projects finds way too many side projects, make free-time fails, git commit fix: everything deletes 4096 lines."
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{escape(alt)}"><title>{escape(alt)}</title><defs>{"".join(defs)}</defs>'
            f'<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>'
            f'<path d="M0 12a12 12 0 0 1 12-12h{W - 24}a12 12 0 0 1 12 12v28H0z" fill="{BAR}"/>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{LINE}"/>'
            f'{lights}<text x="{W / 2}" y="25" text-anchor="middle" font-family="{MONO}" font-size="13" '
            f'fill="{MUTED}">me@rxenv: ~</text>'
            f'<g font-family="{MONO}" font-size="{FS}" xml:space="preserve">{"".join(parts)}</g></svg>\n')


LOGIN = "RexSAS"
QUERY = """query($login: String!) { user(login: $login) {
  contributionsCollection { contributionCalendar { totalContributions
    weeks { contributionDays { contributionCount } } } }
  followers { totalCount }
  repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
    totalCount nodes { stargazerCount languages(first: 10) { edges { size node { name color } } } } } } }"""


def streaks(counts):
    """(current, longest) run of days with contributions; today may still be 0 without breaking the run."""
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    days = counts[:-1] if counts and not counts[-1] else counts
    current = 0
    for c in reversed(days):
        if not c:
            break
        current += 1
    return current, longest


assert streaks([1, 1, 0, 1, 1, 1]) == (3, 3)
assert streaks([1, 1, 1, 0]) == (3, 3)  # nothing yet today
assert streaks([1, 0, 0]) == (0, 1)
assert streaks([]) == (0, 0)

# (value, median, weight): each stat scores 1 - 0.5^(value/median), like github-readme-stats' rank
GRADES = [(0.88, "A+"), (0.80, "A"), (0.72, "A-"), (0.64, "B+"), (0.56, "B"), (0.48, "B-"), (0.40, "C+"), (0, "C")]


def grade(stats):
    score = sum(w * (1 - 0.5 ** (v / m)) for v, m, w in stats) / sum(w for _, _, w in stats)
    return score, next(g for t, g in GRADES if score >= t)


assert grade([(0, 1, 1)]) == (0, "C")
assert grade([(1, 1, 1)])[1] == "B-"  # exactly the median scores 0.5
assert grade([(100, 1, 1)])[1] == "A+"


def fetch():
    for attempt in range(3):  # GitHub's GraphQL API throws the odd transient 502
        r = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={LOGIN}"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)["data"]["user"]
        time.sleep(5 * (attempt + 1))
    raise SystemExit(f"gh api graphql failed: {r.stderr.strip() or r.stdout.strip()}")


def stats_svg(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    current, longest = streaks([c for w in weeks for c in w])
    repos = user["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    langs = {}
    for r in repos["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            size, color = langs.get(n, (0, None))
            langs[n] = (size + e["size"], e["node"]["color"] or MUTED)
    total = sum(s for s, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]

    score, letter = grade([(cal["totalContributions"], 250, 2), (stars, 20, 1), (longest, 14, 1),
                           (repos["totalCount"], 10, 1), (user["followers"]["totalCount"], 10, 1)])
    W, H = 900, 400
    p = [f'<text x="28" y="72" fill="{GREEN}">{escape(PROMPT)}<tspan fill="{INK}">git stats --last-year</tspan></text>']
    rows = [("commits & co.", f"{cal['totalContributions']:,}"), ("current streak", f"{current} days"),
            ("longest streak", f"{longest} days"), ("public repos", str(repos["totalCount"])),
            ("stars", f"{stars} ★" if stars else "0 ★ (be the first)")]
    for i, (k, v) in enumerate(rows):
        y = 112 + i * 26
        p.append(f'<text x="28" y="{y}" fill="{MUTED}">{escape(k)}</text>'
                 f'<text x="330" y="{y}" text-anchor="end" fill="{SAND}">{escape(v)}</text>')
    for i, (name, (size, color)) in enumerate(top):
        y, pct = 112 + i * 26, size / total
        p.append(f'<text x="380" y="{y}" fill="{INK}">{escape(name)}</text>'
                 f'<rect x="500" y="{y - 11}" width="190" height="10" rx="5" fill="{LINE}"/>'
                 f'<rect x="500" y="{y - 11}" width="{max(4, 190 * pct):.1f}" height="10" rx="5" fill="{color}"/>'
                 f'<text x="745" y="{y}" text-anchor="end" fill="{MUTED}">{pct:.0%}</text>')
    peak = max((c for w in weeks for c in w), default=0) or 1
    circ = 2 * 3.14159 * 44  # grade ring: arc length shows the score
    p.append(f'<circle cx="820" cy="160" r="44" fill="none" stroke="{LINE}" stroke-width="8"/>'
             f'<circle cx="820" cy="160" r="44" fill="none" stroke="{ACCENT}" stroke-width="8" stroke-linecap="round" '
             f'stroke-dasharray="{circ * score:.1f} {circ:.1f}" transform="rotate(-90 820 160)"/>'
             f'<text x="820" y="172" text-anchor="middle" font-size="34" font-weight="700" fill="{INK}">{letter}</text>'
             f'<text x="820" y="232" text-anchor="middle" font-size="13" fill="{MUTED}">grade</text>')
    cells = []
    for x, w in enumerate(weeks[-53:]):
        for y, c in enumerate(w):
            op = 0 if not c else 0.3 + 0.7 * min(1, c / peak)
            fill = f'fill="{ACCENT}" fill-opacity="{op:.2f}"' if c else f'fill="{LINE}"'
            cells.append(f'<rect x="{28 + x * 16}" y="{256 + y * 16}" width="12" height="12" rx="2" {fill}/>')
    alt = (f"Git stats, last year: {cal['totalContributions']} contributions, current streak {current} days, "
           f"grade {letter}, longest {longest} days, {repos['totalCount']} public repos, {stars} stars. Top languages: "
           + ", ".join(f"{n} {s / total:.0%}" for n, (s, _) in top))
    lights = "".join(f'<circle cx="{24 + k * 20}" cy="20" r="6" fill="{c}"/>' for k, c in enumerate([ACCENT, SAND, GREEN]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{escape(alt)}"><title>{escape(alt)}</title>'
            f'<rect width="{W}" height="{H}" rx="12" fill="{BG}"/>'
            f'<path d="M0 12a12 12 0 0 1 12-12h{W - 24}a12 12 0 0 1 12 12v28H0z" fill="{BAR}"/>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{LINE}"/>'
            f'{lights}<text x="{W / 2}" y="25" text-anchor="middle" font-family="{MONO}" font-size="13" '
            f'fill="{MUTED}">me@rxenv: ~</text><g font-family="{MONO}" font-size="16">{"".join(p)}</g>'
            f'{"".join(cells)}</svg>\n')


OUT.write_text(build())
(OUT.parent / "stats.svg").write_text(stats_svg(fetch()))
print("ok: terminal.svg, stats.svg")
