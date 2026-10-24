# Issue Tracker Setup

Per-platform setup for the SDD intake flow. The flow itself is identical everywhere; only
the label, dependency-link, and PR-link mechanisms differ. See `rules/issue-intake.md`
(agent rule) and `docs/04-issue-tracker.md` (human guide).

**Status is derived from the branch name and `specs/`; the board only displays it.** The GitHub
Projects board is implemented (`orchestration/tools/sdd-board.sh`, `integration/ci/sdd-board.yml`,
config `.sdd/board.json`, Actions secret `SDD_APP_PRIVATE_KEY` for a GitHub App, or `SDD_PROJECT_TOKEN` as a fallback: classic PAT with `repo` (for private repositories), `project`, `read:org`; see `docs/04-issue-tracker.md`). GitLab and Azure DevOps boards are
tracked in #71 and #72; Bitbucket is out of scope (its Issues are being sunset).

## Branch protection (all platforms)

Protect `main` so that **no one — including administrators — can push directly**.
All changes must go through a pull request / merge request.

### GitHub

Settings → Branches → Add rule, pattern `main`:
- ✅ Require a pull request before merging
- ✅ Include administrators

Or via CLI:
```bash
gh api repos/{owner}/{repo}/branches/main/protection -X PUT \
  --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null
}
EOF
```

### GitLab

Settings → Repository → Protected Branches → Protect `main`:
- Allowed to push and merge: **No one** (force all changes through MRs)
- Allowed to merge: Maintainers (or Developers)

### Bitbucket

Repository settings → Branch permissions → Add permission for `main`:
- Write access: remove all users/groups (or set to **No one**)
- Merge via pull request only

### Azure DevOps

Project Settings → Repositories → select repo → Policies → Branch policies → `main`:
- ✅ Require a minimum number of reviewers (set to 0 for solo projects)
- This alone blocks direct pushes and requires a PR

---

## GitHub (baseline)

Create the three Tier labels (idempotent):

```bash
bash vendor/ai-sdd-guide/integration/issue-tracker/labels.sh           # current repo
bash vendor/ai-sdd-guide/integration/issue-tracker/labels.sh owner/repo
```

- Dependencies: link issues with **Relationships** (blocks / blocked by).
- PR ↔ issue: put `closes #N` in the PR description.

## GitLab

- Tier labels: create `sdd::tier-0/1/2` (scoped labels) under **Project → Labels**, or via
  `glab label create --name "sdd:tier-2" --color "#d93f0b"`.
- Dependencies: **Linked issues** (blocks / is blocked by).
- MR ↔ issue: `Closes #N` in the MR description.

## Bitbucket

- Tier labels: Bitbucket issues have no native labels — use the issue **Kind/Priority**
  fields or a `sdd:tier-N` token in the title/component, depending on your plan.
- Dependencies: **Linked issues**.
- PR ↔ issue: `closes #N` in the PR description.

## Azure DevOps

- Tier labels: apply **Tags** `sdd:tier-0/1/2` (or an **Area** path) to the Work Item.
- Dependencies: **Links** → Predecessor / Successor.
- PR ↔ work item: reference `AB#N` in the PR description or a commit message.

---

After labels exist, the agent follows `rules/issue-intake.md`: read the labeled issue,
create the `t<Tier>/<Issue番号>-<名前>` branch, run the Tier-appropriate SDD flow, and link the PR back.
