# Cut a release

release-please cuts every release from the commit history. You never edit a
version by hand. The release is created as a **draft**, so nothing reaches
PyPI until you publish it yourself. This page shows what runs, in what order,
and where you are expected to intervene.

## The flow

```mermaid
flowchart TD
    accTitle: How a merged change reaches PyPI
    accDescr {
        A push to main runs ci.yml, which holds four jobs: lint, type-check,
        test and docvet. The same push starts release-please.yml, which opens
        a release pull request carrying the version bump and the CHANGELOG
        entry. An update-lockfile job then commits uv.lock onto that same
        release pull request, because release-please bumps pyproject.toml and
        leaves the lockfile behind. Merging the release pull request makes
        release-please cut a GitHub Release as a draft. A draft carries no
        published release event, so nothing downstream runs. You edit the
        draft notes and publish the release by hand. Publishing emits the
        release published event, which starts publish.yml: it builds the
        distribution and uploads it to PyPI over OIDC trusted publishing,
        with no stored token anywhere in the path.
    }

    push["Push to main"] --> ci["ci.yml<br/>lint · type-check · test · docvet"]
    push --> rp["release-please.yml"]
    rp --> relpr["Release PR<br/>version bump and CHANGELOG"]
    relpr --> lock["update-lockfile job<br/>commits uv.lock"]
    lock --> mergerel["You merge the release PR"]
    mergerel --> draft(["Draft release and tag.<br/>No published event.<br/>Nothing downstream runs."])
    draft --> human["You edit the notes,<br/>then publish by hand"]
    human --> pub(["publish.yml<br/>build, then PyPI over OIDC"])
```

## What you do, and what you never do

| step | who |
|---|---|
| land conventional commits on `main` | you, normally |
| open the release PR, bump versions, write the CHANGELOG | release-please |
| refresh `uv.lock` on the release branch | the `update-lockfile` job |
| merge the release PR | **you** |
| cut the draft release and its tag | release-please |
| edit the draft notes and publish | **you** |
| build and upload to PyPI | `publish.yml`, over OIDC |

Never edit a version by hand. Four places carry it — `pyproject.toml`,
`__version__` in `src/judgevet/__init__.py`, `.release-please-manifest.json`
and `uv.lock` — and release-please moves all four together. Editing one makes
them disagree silently.

## Before you merge the release PR

The PR body carries the checklist. The item worth dwelling on is
`STATUS.md`'s verified-versus-inferred table: a release publishes claims, and
that table is where this project records which claims a call has actually
exercised. If a line moved from inferred to verified without a call that did
it, stop.

## Publishing the draft

Publishing is the only irreversible step, and it is deliberately manual.
`publish.yml` triggers on `release: types: [published]` — not on a push, not
on a tag, not on a merge. Until someone clicks publish, nothing can reach the
index.

Edit the draft notes first. The generated CHANGELOG says what changed;
the release notes should say what the release is *for*.

## Testing the path without publishing

`test-publish.yml` is `workflow_dispatch` only and uploads to TestPyPI. The
`testpypi` index in `pyproject.toml` sets `explicit = true`, so dependency
resolution never reaches it — that is a supply-chain property, not a
convenience, and it should stay.

## When release-please fails

If the run fails with `Resource not accessible by personal access token`,
`RELEASE_PLEASE_TOKEN` is under-scoped. It needs three permissions, not two:

| token type | what to set |
|---|---|
| fine-grained | Contents read/write, Pull requests read/write, **Issues read/write**, scoped to this repository |
| classic | `repo` |

Issues is the one that gets missed: GitHub routes pull request *labels*
through the Issues API, and release-please labels its release PRs.

**Never test a token change by re-running the failed job.** A re-run reuses
that run's secret snapshot, so the old token is used again and the fix looks
like it did nothing. Push a commit instead — release-please runs on every push
to `main`, so the next one tests it for free.
