# Judge commit types in shadow mode

`scripts/check_commit_msg.py` checks the form of a commit message.
It checks the type vocabulary, the subject shape and the issue reference.
It cannot tell whether the type fits the change.
It also cannot tell whether a `feat` or `fix` commit finishes its issue, so it only warns when `Closes` and `Refs` are both absent.
This recipe asks a judgment model both questions at the `commit-msg` stage and logs the answers.
It never fails a commit.

## The questions

`commit_questions.json` holds two Choice questions.

| key | instruction | labels |
|---|---|---|
| `type` | Which Conventional Commits type fits this change? | `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `test` |
| `closes` | Does this commit finish the issue it names? | `closes`, `refs` |

The `type` labels equal `TYPES` in `scripts/check_commit_msg.py`.
A unit test compares the two, so they cannot drift.
Each label carries a description, because the descriptions define the labels.
Thin descriptions lowered agreement in #308.

Conventional Commits 1.0.0 defines `feat` and `fix`.
It allows other types and names `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf` and `test` as examples.
Source: https://www.conventionalcommits.org/en/v1.0.0/.
This repository uses nine of those types and does not use `style`.
The descriptions of the other seven types follow how this repository uses them.
For example, `chore` covers agent settings, hook settings and release bookkeeping here.

The `closes` label means the commit completes every remaining Done-when item of the issue.
The `refs` label means partial, preparatory or follow-up work.

## The state

A git `commit-msg` hook receives one argument: the path of the file that holds the proposed message.
Source: https://git-scm.com/docs/githooks#_commit_msg.
It does not receive the Claude Code hook JSON on stdin.
`commit_shadow.py` builds that JSON and passes it to `shadow_judge.py`.

The state holds three fields:

| field | content |
|---|---|
| `subject` | The subject line without its type, such as `cli: add a --quiet flag`. |
| `body` | The body and footers. A `Closes #N` or `Refs #N` footer becomes `Issue: #N`. |
| `diff_stat` | The output of `git diff --cached --stat`. |

The wrapper removes the type and the issue verdict, so the model judges the change without the author's own labels.
The record logs the `commit-msg` event name, the answers and the latency.
It never holds the state.

The wrapper always exits 0.
A missing message file, a provider error, a provider bug and a provider exit all exit 0.
An error the wrapper does not expect also exits 0.
Its stderr line and its log record name the error type only.

## Add the hook

pre-commit runs a hook at the `commit-msg` stage when the hook lists that stage.
Source: https://pre-commit.com/#confining-hooks-to-run-at-certain-stages.
A `commit-msg` hook receives one file name, the file that holds the commit message.
A nonzero exit code aborts the commit.
Source: https://pre-commit.com/#commit-msg.
The wrapper reads the message file from its last argument.
`always_run` runs the hook even when no staged file matches.
`verbose` prints the hook output even when the hook passes.
Source: https://pre-commit.com/#pre-commit-configyaml---hooks.

Add this local hook to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: commit-shadow
        name: commit type shadow check
        entry: uv run --with my-app examples/agent-hooks/commit_shadow.py --provider my_app.judge:provider --model my-model --question examples/agent-hooks/commit_questions.json --timeout 10
        language: system
        stages: [commit-msg]
        always_run: true
        verbose: true
```

Then install the `commit-msg` hook type:

```bash
uv run pre-commit install -t commit-msg
```

The log goes to `$XDG_STATE_HOME/judgevet/shadow.jsonl` unless `--log` names another file.

The hook runs before git writes the commit, so each commit waits for both questions.
The measured latency per commit is in the next section.
`git diff --cached` compares the index with `HEAD`.
Source: https://git-scm.com/docs/git-diff.
After `git commit --amend`, the diff stat therefore shows only the newly staged changes.
The state then omits the rest of the amended commit.

## Measure agreement

`measure_commit_types.py` reads past commits from `git log --stat`.
It skips merge commits and release-please commits, whose subject starts with `chore(main): release`.
It also skips a commit whose subject has no type from the nine labels.
It builds the state that `commit_shadow.py` builds, with the diff stat of the commit itself.
It asks both questions in one call per commit.
It reports type agreement with the written type, Cohen's kappa and the confusion matrix.
It reports `closes` and `refs` agreement on the commits whose footer has exactly one of `Closes` and `Refs`.
It also reports the p50 and p95 latency per call.

```bash
uv run --with my-app examples/agent-hooks/measure_commit_types.py --provider my_app.judge:provider --model my-model --ref main --limit 200
```

A run on 2026-10-09 used local Gemma 4 through typevet 0.8.1 and judgevet 0.18.1.
The model was `gemma-4-31b-qat-q4_0-mm` on llama.cpp.
It read the last 200 eligible commits on `origin/main` at `55d2e14`.
Another job may have shared the local server during the run.

### Type

The judged type agreed with the written type on 145 of 200 commits, or 0.725.
Cohen's kappa was 0.676.
Rows are the written type, and columns are the judged type.

| written \ judged | build | chore | ci | docs | feat | fix | perf | refactor | test |
|---|---|---|---|---|---|---|---|---|---|
| build | 6 | 1 | 7 | 0 | 0 | 1 | 0 | 0 | 0 |
| chore | 8 | 15 | 0 | 1 | 0 | 1 | 0 | 0 | 0 |
| ci | 1 | 0 | 15 | 0 | 0 | 0 | 1 | 0 | 0 |
| docs | 0 | 11 | 0 | 32 | 0 | 0 | 0 | 1 | 0 |
| feat | 1 | 0 | 0 | 0 | 38 | 6 | 0 | 1 | 3 |
| fix | 1 | 0 | 2 | 0 | 1 | 10 | 0 | 0 | 0 |
| perf | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| refactor | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 |
| test | 0 | 0 | 2 | 1 | 2 | 2 | 0 | 0 | 25 |

The largest confusions were `docs` judged `chore` (11), `chore` judged `build` (8) and `build` judged `ci` (7).
The five most confident disagreements each had confidence 1.000:

| commit | written | judged | subject |
|---|---|---|---|
| `9d4941004` | `docs` | `chore` | docs: add the social preview card and decline Sonar |
| `9297cf92f` | `test` | `fix` | test(gates): drop GIT_* variables from configuration hook children |
| `7cb245054` | `build` | `ci` | build: make the module cap a hard 300 code lines |
| `741f19806` | `build` | `chore` | build: name the file-size hook after its single limit |
| `17f24f353` | `feat` | `fix` | feat(http): read Ollama's error body and pin its documented response |

Some of these disagreements are defensible readings of the change.
A disagreement is a prompt for review, not proof that the written type is wrong.

### Closes or Refs

138 of the 200 commits had exactly one of `Closes` and `Refs` in a footer.
The judged verdict agreed on 107 of them, or 0.775.
Cohen's kappa was 0.221.


| written \ judged | closes | refs |
|---|---|---|
| closes | 101 | 0 |

The model judged `closes` for 132 of the 138 commits.
It found 6 of the 37 `refs` commits.
The state does not hold the issue text, so the model cannot see the Done-when items.
**Open question:** whether adding the issue's Done-when list to the state raises agreement on `refs`.

### Latency

One call asks both questions.
The p50 latency per call was 2.91 seconds and the p95 latency was 4.80 seconds.
The run had no errors.
A synchronous `commit-msg` hook adds about that wait to each commit.
