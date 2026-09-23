---
status: draft
---

# Write and review technical prose

Status: **draft**.

Write for the reader's task. Use familiar words, name the actor and give one
instruction per sentence. State a concrete fact or mark an open question.
Use the [glossary](../reference/glossary.md) for domain terms.

This local profile is informed by
[ASD-STE100](https://www.asd-ste100.org/about_STE.html).
That standard includes writing rules and a controlled dictionary with approved
meanings and parts of speech. This project does not establish those properties
and does not claim ASD-STE100 compliance.

## Run the mechanical check

```bash
uv run python -m scripts.check_plain_english
```

The enabled commit, push and CI checks run the same command over the whole
scope. A finding prints its file, the containing prose block's starting line,
and the failed rule. Split a long sentence or replace an adjective with the
specific behavior. Do not add a suppression or hide prose in code formatting.

The profile checks two rules:

- Use at most 25 words per sentence. The same limit applies to an unpunctuated
  heading, list item, table cell or paragraph.
- Do not use `seamless`, `robust`, `powerful`, `blazing` or `cutting-edge` as
  prose words. Matching ignores case and requires a whole word.

The 25-word limit is a local policy, not a claim to implement STE sentence rules.
The checker counts letter/number groups, including numbers. Apostrophes, hyphens
and internal periods keep a group together. It splits sentences at a period,
question mark or exclamation mark followed by whitespace or the block's end.
It recognizes `e.g.`, `i.e.`, `etc.`, `vs.`, `Dr.`, `Mr.` and `Mrs.` as
abbreviations. Other abbreviation boundaries need editorial attention.

## Scope and syntax

The check reads README, SECURITY, every authored Markdown page under `docs/`,
and module, class and function docstrings under `src/judgevet/`.
Maintainer pages follow the same rules as user pages. Public and private package
docstrings have the same scope.

Markdown parsing retains headings, list items, table cells, blockquotes and
visible link labels. It excludes fenced and indented code, inline code,
URL destinations, raw URLs, HTML syntax/comments and YAML frontmatter.
Write literal public identifiers and wire fields as code. Image descriptions
remain prose. Raw HTML blocks are outside the parser's prose model; write
reader guidance in Markdown, not HTML.

Python parsing reads actual AST docstrings, not comments or arbitrary strings.
Google section labels and parameter/type prefixes do not count as prose.
Their descriptions remain checked. Fenced examples and doctest input/output
are excluded. Diagnostics identify source lines, not generated reference lines.

STATUS and repository agent instructions are working evidence and agent rules,
not user documentation in this check. Tooling scripts and tests are outside the
package-docstring scope. Generated reference pages use the checked source
strings. This scope does not exempt individual authored documentation files.

## Review what the checker cannot decide

A green check does not establish grammatical or technical correctness.
Review a documentation change in its reading path:

- Identify the audience and the question the page answers. Keep tutorials,
  task guides, explanations and lookup reference distinct.
- Check prerequisites, complete inputs, expected outcomes and recovery steps.
  Follow links as a reader would, without relying on issue history.
- Name the actor and prefer active voice. Keep one instruction per sentence
  and avoid stacked qualifications. Read each paragraph for a connected idea.
- Check the meaning of score, confidence, probability and local acceptance.
  A lexical check cannot prove that a number has the right interpretation.
- Preserve citations and verified/inferred boundaries. Do not imply calibration,
  universal redaction, guaranteed correctness or capabilities that have not shipped.
- Keep literal identifiers accurate. Use the
  [example and link checks](build-docs.md) to verify executable claims.

Do not shorten prose by removing a prerequisite, a security limit or an evidence
qualification. Rewrite the explanation so each necessary fact remains clear.

## Check terminology

```bash
uv run python -m scripts.check_terminology
```

The same README, SECURITY, authored-docs and package-docstring scope applies.
The checker reads preferred and avoided terms from the glossary table. It has
no second term list. Changing a preferred term changes its diagnostic.
Malformed or missing tables fail the check.

The table's Check column selects these explicit contexts:

| Selector | Lexical scope |
|---|---|
| `question` | An avoided word after Jev, evaluation or judgment; or before “to Jev” or “for Jev”. |
| `answer` | After Noul, Choice, Score, named question, individual question or per-question; or before “for a/one/each [named] question”. |
| `confidence` | After Choice, Score or model; or before “of [the] Choice/Score”. |
| `boundary` | After judgevet, typed, SystemOnePort or AsyncSystemOnePort. |
| `adapter` | After HTTP, CLI, MCP, SystemOnePort, AsyncSystemOnePort or judgevet. |
| `always` | The avoided phrase anywhere in extracted prose. |
| `human` | Semantic review only; no lexical substitution. |

Matching ignores case and recognizes a simple plural ending in `s` or `ies`.
It does not infer the subject of arbitrary sentences. An HTTP response, a
function result and a Bash prompt remain valid technical terms. An ambiguous
standalone word remains for review. Score versus confidence and documented
versus live verified require evidence and context that lexical matching cannot establish.

Inline/fenced code preserves exact identifiers, wire fields and quoted
diagnostics. Citation destinations are excluded; descriptive link labels remain
prose. Quote an exact diagnostic as code, while keeping its explanation in prose.
These are syntax rules, not exceptions for individual files.

For Python identifiers, the check reads only annotated local variable names
with directly imported judgevet question or individual-answer types.
It recognizes imports from the package root and domain question/answer modules,
including aliases. It checks underscore-delimited words against the corresponding
glossary row. Public definitions, parameters, class attributes, module bindings,
wire keys and `SystemOneResponse` containers retain their contract names.
Unannotated locals, qualified annotations and compound type expressions require
review; the checker does not infer their runtime type.

The command runs in commit/push hooks and CI. A clean lexical check does not
prove that every term or numeric interpretation is correct.

## Optional model-assisted editorial review

The [CLI policy workflow](../how-to/use-cli-policy.md) can ask a Noul question
about a passage and compare its answer with a local acceptance threshold.
An agent can also use the supported [MCP tools](../reference/mcp.md).
This can assist review of meaning or clarity. It does not replace the exact
lexical check, the reviewer or the recorded evidence for a claim.

Such a review sends the passage and question to the configured service and
requires credentials. Apply the [disclosure guidance](../../SECURITY.md#data-sent-to-the-service)
first. Its probability and a policy pass do not prove editorial correctness.
Ordinary documentation gates stay offline and do not depend on model judgments.
