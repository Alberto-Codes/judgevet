---
status: draft
---

# Use question files and piped state

Status: **draft**.

Prerequisites: [install the CLI](install.md#run-the-cli), use a POSIX shell,
and supply an approved key as described in [credential handling](../../SECURITY.md#credentials).
Calls require service access and disclose their input to Jev.

For a positional invocation, both state and questions are literal arguments:

```bash
judgevet 'A short example.' '{"clear":{"type":"noul","instructions":"Is this text clear?"}}' --json
```

Keep questions in a UTF-8 JSON file using the same shape as the positional
questions argument. For example, save this as `questions.json`:

```json
{"clear":{"type":"noul","instructions":"Is this text clear?"}}
```

Load the API key through your approved environment configuration. Evaluate text
from an argument, a file, or standard input. Create the example state file first:

```bash
printf 'A short example.\n' > document.txt
```

```bash
judgevet 'A short example.' --questions-file questions.json --json
judgevet --state-file document.txt --questions-file questions.json --json
printf 'A short example.\n' | judgevet --state-file - --questions-file questions.json --json
```

Only `--state-file -` reads stdin. The original `judgevet STATE QUESTIONS`
invocation still accepts literal strings, including `-`. With `--state-file`,
use `--questions-file`; a lone positional argument always occupies STATE.
Question paths do not read stdin.

Choose exactly one source for state and one for questions. Repeated file
options, competing sources and missing sources exit 2 before reading input.
File access, UTF-8 decoding and content failures exit 1 before an API request.
Diagnostics identify the source without echoing its contents or path.

Explicit state files and stdin must contain non-whitespace content. Text keeps
its newlines. Content beginning with `[` or `{` is parsed as JSON, just as in
the original positional invocation. Leading whitespace does not trigger JSON
parsing. Question files must contain a nonempty object of named questions;
duplicate object keys and malformed question entries are rejected.

Successful output keeps the existing model, usage and answers envelope.
`--json` sends answers to stdout and handled input errors as JSON to stderr.
Framework argument parsing errors retain their existing format. A valid
judgment exits 0 regardless of its probability; this input feature does not
turn a low probability into an operational failure.

To turn a judgment into an acceptance decision, use an [explicit policy](use-cli-policy.md).
That guide shows how automation handles exits 0, 1, 2 and 3. If the command
fails, use [troubleshooting](troubleshoot.md); do not publish unreviewed stderr.

For the full contract, see the [CLI reference](../reference/cli.md).

## Supply local image evidence

An application that selects a media provider with `create_cli_app` can accept
`--evidence-file PATH` before or after the positional inputs. Specify it once.
The installed hosted command rejects nonempty image evidence before reading
credentials or constructing HTTP. It does not send images to Jev.

The manifest is a UTF-8 JSON object with exactly `images`, `by_question` and
optional `required`. For example, its contents may be
`{"images":[{"id":"scan","path":"scan.png","media_type":"image/png"}],"by_question":{"clear":["scan"]},"required":["clear"]}`.
Each image declares nonempty `id`, `path` and `media_type` strings.
`by_question` maps existing question IDs to ordered image ID lists.
`required` lists questions that must have evidence and defaults to empty.
Every image must be referenced. IDs and references cannot repeat within their lists.

Relative image paths resolve against the manifest directory. Absolute local
paths are accepted; network URLs are rejected. The CLI preserves exact bytes,
attachment order and per-question order. It never decodes images or embeds them
in state. MIME is a declaration, not a guarantee about decoded content.

The manifest limit is 1 MiB. Evidence allows at most 16 images, 8 MiB per image
and 32 MiB total. Duplicate JSON keys, unknown fields, non-finite constants,
invalid UTF-8, malformed structures and missing references fail before provider
acquisition. Diagnostics identify `--evidence-file` and the failure category
without printing paths or contents. These failures and repeated evidence flags
exit 1. A valid empty optional manifest uses the existing text path.
Provider capability declarations apply additional model-specific limits.
Source: [CLI media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851367000).
