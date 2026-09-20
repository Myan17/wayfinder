# Roster — accountable humans, machine accounts, agent tools

Machine-readable block below is parsed by `scripts/check_commit_identity.py` and
`scripts/gen_codeowners.py`. Keep the YAML and the prose in sync; CI reads the YAML.

```yaml
engineers:
  - handle: myan
    name: Myan Gupta
    github: Myan17
    role: implementer              # writes code; every pull request is reviewed by gupta958
    emails:
      - 181651739+Myan17@users.noreply.github.com
    machine_account: null          # optional; one per person is permitted by GitHub's terms
    agents:
      - claude-code/opus-5
    owns: [authz, retrieval, answer, egress, cache, http, web, eval-harness,
           sources, chunking, indexing, webhooks, eval-data, platform, observability]

  - handle: gupta958
    name: Engineer B
    github: Gupta958
    role: reviewer                 # reviews and merges; does not author implementation pull requests
    emails:
      # A public repository is scraped: keep personal addresses out of it. If gupta958 ever authors
      # a commit, put their GitHub no-reply address here (Settings > Emails > "Keep my email
      # addresses private"), not a university or personal one.
      - <GUPTA958_GITHUB_NOREPLY>
    machine_account: null
    agents:
      - chatgpt                    # assists review only; review comments it drafts are marked [agent-draft]
    owns: []
    reviews: ["*"]                 # required reviewer on every path

joint_modules: [schema, agreements]   # still need an explicit second opinion, which is gupta958's approval

rules:
  author_must_be_engineer_or_their_machine_account: true
  required_trailers: [Agent, Operator, Session, Task]
  conventional_commit_scopes_from: docs/team/OWNERSHIP.md
```

## Notes

- **Emails** must match `git config user.email` in every worktree, and must be GitHub no-reply
  addresses: this repository is public. The GitHub no-reply address keeps a
  personal address out of a public repository while still attributing the commit.
- **Machine accounts** are optional. Use one only if you want agent-authored commits to appear under a
  distinct author; GitHub's terms allow one machine account per person, and creating extra personal
  accounts is not an option.
- **Agent strings** are `<tool>/<model>`; add a row when either changes, because the digest groups by
  it and a capability change is worth seeing in the history.
- A person leaving the project stays in the roster with `active: false` so old commits still validate.
- **Roles are current, not permanent.** If `gupta958` starts implementing, move the affected modules
  into their `owns:` list, set `role: implementer`, regenerate `CODEOWNERS`, and update the ownership
  table — one pull request, both approving. Nothing else in the framework changes: the cards, logs and
  guardrails already assume more than one implementer.
