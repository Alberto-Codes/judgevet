---
status: draft
---

# Documentation

Status: **draft**. Choose a path by what you need to do.

## Tutorials: learn through a first task

- [Make your first judgment](tutorials/first-judgment.md): install, ask one
  Noul question and interpret its typed answer.
- [Make your first local policy decision](tutorials/first-policy.md): compare
  synthetic answers with an inclusive threshold, without a service call.

## How-to: complete a task

- [Install the library or CLI](how-to/install.md#install-the-library).
- [Call from synchronous Python](how-to/use-library.md) or
  [asynchronous Python](how-to/use-async-library.md).
- [Test code that calls Jev without a network](how-to/test-offline.md).
- [Handle failed library calls](how-to/handle-errors.md).
- [Connect VS Code, Cursor, Claude Code, Desktop or Codex](how-to/connect-mcp.md).
- [Use judgevet through Pi's CLI access](how-to/connect-mcp.md#pi-cli-access).
- [Use a self-hosted judgment provider](how-to/use-a-self-hosted-provider.md).
- [Use Ollama as a local server](how-to/use-ollama.md).
- [Use judgevet in an agent harness](how-to/use-in-an-agent-harness.md).
- [Diagnose installation, input and connection failures](how-to/troubleshoot.md).
- [Read questions from files and state from files or stdin](how-to/use-cli-files.md).
- [Apply an acceptance policy in the CLI](how-to/use-cli-policy.md).
- [Construct, decode and evaluate a policy in Python](how-to/use-policy-library.md).
- [Own synchronous and asynchronous adapter lifecycles](how-to/use-policy-library.md#own-the-adapter-lifecycle).
- [Handle local policy errors](how-to/use-policy-library.md#handle-errors-and-immutable-values).
- [Review staged Git changes](how-to/review-staged-diff.md).

- [Deploy a CLI job or integrate the library in a serverless runtime](how-to/deploy.md).

## Reference: look up a contract

- [Question types, typed answers, adapters and ports](reference/api.md).
- [CLI options, inputs, output and exit codes](reference/cli.md).
- [MCP tool schemas and answers](reference/mcp.md).
- [Policy types, JSON grammar and evaluation](reference/policy.md).
- [Supported imports and compatibility](reference/compatibility.md).
- [Configuration defaults and precedence](reference/configuration.md).
- [Diagnostic events and caller correlation](reference/events.md).
- [Service, transport and local policy errors](reference/errors.md).
- [Verified and inferred service claims](reference/verification-ledger.md).
- [Terms and meanings](reference/glossary.md).
- [Worker run contract and commit trailers](reference/worker-runs.md).
- [The installed typing marker](reference/py-typed-marker.md).
- [Credential inputs and precedence](../SECURITY.md#credentials).
- [Data disclosure and diagnostic limits](../SECURITY.md#data-sent-to-the-service).

## Explanation: understand the decisions

- [Choose between Noul, Choice and Score](explanation/judgments.md).
- [Understand local acceptance policies and threshold tradeoffs](explanation/policies.md).
- [Distinguish local checks, live observations and model quality](explanation/verification.md).
- [Security boundaries and caller responsibilities](../SECURITY.md).
- [Choose an entry point and understand ownership](explanation/architecture.md).

## Maintainers

Start with [contributor setup](maintainers/contributor-setup.md) for a fresh checkout.
[Maintainer procedures](maintainers/index.md) cover wheel verification and
release operations. They are separate from package use.

- [Write and review technical prose](maintainers/writing-guide.md).
- [Build and check documentation](maintainers/build-docs.md).
- [Verify package typing](maintainers/verify-package.md).
- [Cut and verify a release](maintainers/cut-a-release.md).
- [Publish the MCP registry listing](maintainers/mcp-registry.md).
- [Delegate a bounded change](maintainers/delegate-work.md).

The former [release-guide path](how-to/cut-a-release.md) remains a pointer for
existing links. The [verification ledger](reference/verification-ledger.md)
holds current verification evidence; users do not need it to follow the task guides.
