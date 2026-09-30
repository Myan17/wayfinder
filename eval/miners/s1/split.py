"""ADR-0013 D-5: group by shared issue or PR, then split temporally per repository by group."""

from __future__ import annotations

from collections import Counter, defaultdict

SPLITS = (("dev", 0.5), ("test", 0.8), ("held_out", 1.01))


def _groups(ps: list[dict]) -> list[list[int]]:
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in ps:
        a, b = find(("i", p["repo_id"], p["issue"])), find(("p", p["repo_id"], p["pr"]))
        parent[a] = b
    comps: dict = defaultdict(list)
    for i, p in enumerate(ps):
        comps[find(("p", p["repo_id"], p["pr"]))].append(i)
    return list(comps.values())


def assign(ps: list[dict]) -> dict:
    """Each pair gets group_id, t_g and split. Weak pairs are passed in too (step 6).

    Returns the annotated pairs, achieved counts per repository, and each repository's two
    boundary times (the t_g of its first test group and first held-out group).
    """
    groups = []
    for members in _groups(ps):
        repos = Counter(ps[i]["repo_id"] for i in members)
        top = max(repos.values())
        # Step 3. Nodes are keyed by repository and S1-2 counts same-repository closing
        # references only, so a group is single-repository in practice; the rule stays as written.
        repo = min(r for r, n in repos.items() if n == top)
        groups.append(
            {
                "members": members,
                "repo": repo,
                "t": max(ps[i]["merged_at"] for i in members),  # step 2: latest merge
                "first_pr": min(ps[i]["pr"] for i in members),
            }
        )
    out = [dict(p) for p in ps]
    achieved: dict = {}
    boundaries: dict = {}
    for repo in sorted({g["repo"] for g in groups}):
        mine = sorted((g for g in groups if g["repo"] == repo), key=lambda g: (g["t"], g["first_pr"]))
        n = sum(len(g["members"]) for g in mine)  # N: the repository's pairs
        c, counts, bounds = 0, {"dev": 0, "test": 0, "held_out": 0}, {}
        for g in mine:
            name = next(s for s, frac in SPLITS if c < frac * n)
            bounds.setdefault(name, g["t"])
            gid = f"{repo}:{g['first_pr']}"
            for i in g["members"]:
                out[i].update(group_id=gid, t_g=g["t"], split=name)
            counts[name] += len(g["members"])
            c += len(g["members"])
        achieved[repo] = counts
        boundaries[repo] = {"test_from": bounds.get("test"), "held_out_from": bounds.get("held_out")}
    return {"pairs": out, "achieved": achieved, "boundaries": boundaries}
