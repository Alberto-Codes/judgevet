---
status: draft
---

# Documentation

Status: **draft**. Choose a path by what you need to do.

## Tutorials: learn through a first task

Dedicated first-judgment and first-policy tutorials are still being written.
For now, [install the package](how-to/install.md), then run the
[README library quick start](../README.md#use-the-typed-library).
The [Python policy guide](how-to/use-policy-library.md#construct-a-typed-policy)
contains an offline example with synthetic answers. These are starting points,
not complete guided tutorials.

## How-to: complete a task

- [Install the library or CLI](how-to/install.md#install-the-library).
- [Connect an MCP host](how-to/install.md#run-the-published-mcp-command),
  [verify discovery](how-to/install.md#verify-the-connection), or
  [troubleshoot initialization](how-to/install.md#when-mcp-does-not-connect).
- [Read questions from files and state from files or stdin](how-to/use-cli-files.md).
- [Apply an acceptance policy in the CLI](how-to/use-cli-policy.md).
- [Construct, decode and evaluate a policy in Python](how-to/use-policy-library.md).
- [Own synchronous and asynchronous adapter lifecycles](how-to/use-policy-library.md#own-the-adapter-lifecycle).
- [Handle local policy errors](how-to/use-policy-library.md#handle-errors-and-immutable-values).
- [Review staged Git changes](how-to/review-staged-diff.md).

## Reference: look up a contract

- [Question types, typed answers and HTTP adapter examples](reference/api.md).
- [Supported imports and compatibility](reference/compatibility.md).
- [Terms and meanings](reference/glossary.md).
- [The installed typing marker](reference/py-typed-marker.md).
- [Credential inputs and precedence](../SECURITY.md#credentials).
- [Data disclosure and diagnostic limits](../SECURITY.md#data-sent-to-the-service).

Complete CLI, MCP, configuration and service-error reference pages are still
being written. Current policy errors are covered in the Python guide above;
the API page is not yet an exhaustive error reference.

## Explanation: understand the decisions

Dedicated explanations of judgments, policies, architecture and evidence limits
are still being written. Current definitions and limits are available in:

- [Probability, confidence, score and local policy decisions](reference/glossary.md#numbers-and-decisions).
- [Ports and adapters](reference/glossary.md#architecture).
- [Observed behavior versus documented expectations](reference/glossary.md#evidence-and-documentation-status).
- [Security boundaries and caller responsibilities](../SECURITY.md).

These lookup sections define terms; they do not replace the planned explanations.

## Maintainers

[Maintainer procedures](maintainers/index.md) cover wheel verification and
release operations. They are separate from package use.
The former [release-guide path](how-to/cut-a-release.md) remains a pointer for
existing links. [STATUS](../STATUS.md) holds current verification evidence;
users do not need its linked issue history to follow the task guides.
