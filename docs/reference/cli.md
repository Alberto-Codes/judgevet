---
status: draft
---

# CLI reference

Status: **draft**. The installed command is `judgevet [OPTIONS] [STATE] [QUESTIONS]`.
It makes judgments through the same typed library. No subcommand is required.
The [CLI source](../../src/judgevet/adapters/inbound/cli.py) and installed
`judgevet --help` define the option surface.

## Arguments and options

| Input | Default | Meaning |
|---|---|---|
| `STATE` | No source | Literal text, or JSON when its first character is `{` or `[`. |
| `QUESTIONS` | No source | JSON object mapping names to question definitions. |
| `--state-file PATH` | None | Read UTF-8 state; `-` reads stdin. At most once. |
| `--questions-file PATH` | None | Read UTF-8 question JSON. At most once; `-` is a filename. |
| `--policy PATH` | None | Read an explicit local JSON acceptance policy. At most once. |
| `--model TEXT` | `jev-latest` | Model sent to the service. |
| `--api-key TEXT` | Settings key | Explicit credential override; prefer the approved environment. |
| `--json` | Off | JSON answers and handled-error output. |
| `--install-completion` | No action | Install completion for the current shell. |
| `--show-completion` | No action | Print shell completion for inspection or installation. |
| `--help` | No action | Print help and exit. |

There is no CLI timeout option; use [configuration](configuration.md). The
settings model default does not override `--model`'s default. Avoid credentials
in shell history or process arguments; see [SECURITY](../../SECURITY.md#credentials).

## Input selection and parsing

Exactly one state source and one question source are required. A positional
source and its file option conflict; repeated file/policy options also fail.
Selection failures exit 2 before reading input. There is no fallback from a
bad file to a positional value.

Positionals keep their order. With `--state-file`, use `--questions-file` too:
a lone positional is always STATE, not QUESTIONS. A positional `-` is literal
text; only `--state-file -` requests stdin.

State files/stdin must be nonempty after whitespace checking. The original text
and newlines are preserved. State parsing tests the original first character:
leading whitespace before `{` or `[` leaves the content as text. Question files
must be nonempty JSON objects with nonempty names, object entries and supported
`type` values; duplicate object keys are rejected. File access, UTF-8 and content
errors exit 1. These stricter file checks do not change the legacy positional
JSON parser into a duplicate-key validator.

Question entries use `type` (`noul`, `choice`, `score`), `instructions` and
`criteria`. The parser defaults missing Choice criteria to `{}` and missing
Score criteria to `[]`; these defaults do not establish valid service input.
Use meaningful question definitions as in the [file guide](../how-to/use-cli-files.md).
[Question semantics](api.md#question-types) cite the vendor definitions.

## Output and exit status

| Exit | Meaning | Expected streams for handled outcomes |
|---|---|---|
| 0 | A valid judgment; if a policy was supplied, it passed | Answers on stdout. |
| 1 | Input, policy-definition or service failure | Diagnostic on stderr; no policy verdict. |
| 2 | Invalid invocation or conflicting/missing sources | Diagnostic on stderr. |
| 3 | Valid judgment whose explicit policy was unmet | Answers and policy report on stdout in JSON mode; stderr empty. |

A low probability alone never changes exit 0. Human output includes model,
usage and answers on stdout. With a policy, human policy summaries/comparisons
use stderr. Logs also use stderr. Startup and unexpected exceptions may fall
outside the handled-error envelope; see [errors](errors.md#adapter-presentation).

`--json` emits an object containing `model`, `usage` and `answers`. `usage` has
`input_tokens` and `output_tokens`. `answers` maps each question name to an
object containing `name`, `type` and the corresponding [answer fields](api.md#answer-and-container-types).
Score integer dictionary keys become strings in JSON. Answer order follows the
returned mapping; it is not sorted by question name.

With `--policy`, an additional `policy` object has `result` (`"pass"` or
`"fail"`) and ordered `rules`. Each rule report has `question`, `pass` (boolean)
and `detail` (comparison text). This is the CLI representation; the Python
report uses `passed`. See [policy grammar](policy.md#json-grammar).

Handled errors in JSON mode use an `error` string on stderr. Framework usage
errors retain their own formatting. Do not parse arbitrary stderr as JSON or
assume error text is redacted. The [automation recipe](../how-to/use-cli-policy.md#distinguish-policy-rejection-in-automation)
shows status-aware handling with separate streams.
