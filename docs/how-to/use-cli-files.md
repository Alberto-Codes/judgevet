---
status: draft
---

# Use question files and piped state

Status: **draft**.

Keep questions in a UTF-8 JSON file using the same shape as the positional
questions argument. For example, save this as `questions.json`:

```json
{"clear":{"type":"noul","instructions":"Is this text clear?"}}
```

Load the API key through your approved environment configuration. Evaluate text
from an argument, a file, or standard input:

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
