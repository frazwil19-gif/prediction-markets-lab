# Phone-Only GitHub Handoff

**No GitHub connector was available in Claude's environment for this
project.** (Confirmed via a live registry search for "github" /
"repository" / "git push" — nothing installed or connected.) This
means Claude cannot push this repository to GitHub directly. This
document explains two ways to get it there anyway, without a laptop.

## Method A — Preferred: use a connected AI GitHub tool (e.g. ChatGPT)

If you have a separate AI assistant session (ChatGPT or otherwise)
with a GitHub connector already set up, this is the easiest path:

1. Download `prediction-markets-lab-stage3a-state-a-with-git-history.zip`
   from this Claude conversation (it contains the complete `.git`
   history — every commit, not just the current file snapshot).
2. Upload that archive into the ChatGPT (or other) conversation that
   has GitHub connected.
3. Ask it to inspect the archive and confirm — **before assuming
   anything** — whether its GitHub connector can:
   - create a new repository,
   - upload/push the repository's contents,
   - preserve or faithfully recreate the commit history (not just
     the latest snapshot),
   - ensure `.github/workflows/cycle_001_data_acquisition.yml` ends up
     in the right place so GitHub recognises it as an Actions workflow.
4. **Do not assume these capabilities exist until the other assistant
   confirms them for its specific connector.** Different GitHub
   integrations vary widely — some can only create files one at a
   time via the API (which would lose commit history), others can
   push a full `git` bundle.
5. If confirmed capable, have it create or update a repository named
   exactly `prediction-markets-lab`.
6. After it reports success, confirm yourself (see "Verification"
   below) — don't take a single "done" message as final proof.

## Method B — Phone-browser fallback using a cloud terminal

If Method A isn't available, use any browser-based Linux terminal or
GitHub Codespace-style environment reachable from your phone's
browser (e.g. GitHub Codespaces itself, once a repo exists to attach
one to — or any other cloud shell you already have access to).

### Step 1 — Create the empty GitHub repository

1. In the GitHub app or mobile browser, create a new repository named
   exactly:
   ```
   prediction-markets-lab
   ```
2. **Do not** initialise it with a README, a licence, or a
   `.gitignore` — leave it completely empty. (If you accidentally add
   any of these, that's fine, just don't add real content — an
   auto-generated README can be overwritten by the push below, but an
   unrelated pre-existing history would complicate things.)

### Step 2 — Get the archive into a cloud terminal

1. Download `prediction-markets-lab-stage3a-state-a-with-git-history.zip`
   to your iPhone's Files app.
2. Open your cloud terminal / browser dev environment.
3. Upload the zip file into it (most browser-based terminals have an
   upload button or drag-and-drop area; some let you `curl` a
   shareable link instead).

### Step 3 — Extract and verify

```bash
unzip prediction-markets-lab-stage3a-state-a-with-git-history.zip
cd prediction-markets-lab
git status
git log --oneline --max-count=10
```

Confirm:
- `git status` runs without error (proves the `.git` directory came
  through intact).
- `git log` shows real commit messages, not an empty history.

### Step 4 — Point it at your new GitHub repository

```bash
git remote -v
```

If this shows no `origin`, add one (replace `<REPOSITORY_URL>` with
the HTTPS or SSH URL GitHub gave you when you created the repo):

```bash
git remote add origin <REPOSITORY_URL>
```

If it already shows an `origin` pointing somewhere else (e.g. left
over from a template), **don't delete and re-add** — just repoint it:

```bash
git remote set-url origin <REPOSITORY_URL>
```

### Step 5 — Confirm the branch name and push

```bash
git branch --show-current
git push -u origin HEAD
```

`HEAD` pushes whatever branch you're currently on to a same-named
branch on GitHub, which avoids needing to know or guess the branch
name in advance.

### A note on credentials

This document deliberately does not include any credential, token, or
password. Whatever cloud terminal you use will prompt you for GitHub
authentication (typically a personal access token, or a device-login
flow) at the `git push` step — follow its own instructions for that;
never paste a token into a document or share it with an AI assistant.

## Verification after upload (either method)

Before considering the handoff complete, confirm on github.com or in
the GitHub app:

- [ ] All expected source files are visible in the repository (spot-check
      `README.md`, `src/prediction_markets_lab/`, `scripts/`).
- [ ] `.github/workflows/cycle_001_data_acquisition.yml` exists and
      GitHub's **Actions** tab lists "Cycle 1 Data Acquisition" as a
      workflow.
- [ ] Commit history is visible (not just a single "initial commit").
- [ ] Actions are enabled for the repository (Settings → Actions, if
      it's a brand-new repo this is usually on by default).
- [ ] No unrelated existing repository content was overwritten — if
      `prediction-markets-lab` already existed with different content
      before this handoff, stop and reconcile manually rather than
      force-pushing over it.
- [ ] The latest commit hash shown on GitHub matches the hash reported
      in Claude's final status report for this archive.

Once all of these are confirmed, proceed to
`docs/PHONE_ONLY_DATA_ACQUISITION.md` to actually run the Cycle 1 data
acquisition workflow.
