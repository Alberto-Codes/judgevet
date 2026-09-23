---
status: draft
---

# Make your first judgment

Status: **draft**.

You will send one support ticket and one Noul question to Jev, read a typed
answer, and explain what its number means. You will not make an automatic
routing decision yet.

## Prepare an isolated environment

Use Python 3.12 or newer and Bash on Linux or macOS. You need network access
for installation and the service call, plus a TypeSafe account with an API key.
Service usage can incur charges. Obtain the key through the
[TypeSafe console](https://console.typesafe.ai/).

Run these commands from a directory where you can create a new folder:

```bash
mkdir judgevet-tutorial
cd judgevet-tutorial
python3 -m venv .venv
.venv/bin/python -m pip install 'judgevet==0.7.0'
.venv/bin/python -c 'import judgevet; print(judgevet.__version__)'
```

Checkpoint: the last command prints `0.7.0`. Keep using this shell and directory.
If the folder already exists, choose a new name. If Python cannot create a
virtual environment, install your platform's venv support and try again.
For other installation approaches, use the [installation guide](../how-to/install.md).

## Supply a key without putting it in your program

If your process already has `JEV_API__KEY` from an approved secret provider,
keep that value. Otherwise, enter the key at this Bash prompt. Input is hidden
and the key is not part of a shell command argument:

```bash
read -r -s -p 'TypeSafe API key: ' JEV_API__KEY
printf '\n'
export JEV_API__KEY
```

Do not print the variable, commit it or turn on shell tracing. This tutorial's
Python program reads that variable and passes the key explicitly. The library
adapter does not load environment credentials itself.

The call sends the ticket text, question instructions and requested model to
the configured service, with the key for authentication. Only send content you
are authorized to disclose. We use synthetic ticket text below. Read the
[security policy](../../SECURITY.md#data-sent-to-the-service) before using real
customer data; judgevet does not establish the service's retention policy.

## Ask one question

Save this complete program as `first_judgment.py` in `judgevet-tutorial`:

```python
import os

from judgevet import HTTPSystemOneAdapter, Noul

with HTTPSystemOneAdapter(api_key=os.environ["JEV_API__KEY"]) as adapter:
    response = adapter.system_one(
        state="I was charged twice. Please help today.",
        questions={"billing": Noul(instructions="Is this about billing?")},
        model="jev-1.13.0",
    )

answer = response.nouls["billing"]
print(f"Probability of billing: {answer.noul}")
print(f"Resolved model: {response.model}")
print(f"Input tokens: {response.usage.input_tokens}")
```

The **state** is the ticket. The **question** asks whether it concerns billing.
`billing` is the name you chose to retrieve that question's answer. Noul
returns a probability of yes, with no separate confidence field. The service
also returns the resolved model and usage. These fields follow the vendor's
[Noul](https://docs.typesafe.ai/primitives/noul) and
[API](https://docs.typesafe.ai/api) definitions.

The `with` block closes the HTTP client when it exits, including when a call
raises. Reading the returned answer afterwards does not require an open client.
Run the file with the interpreter where you installed judgevet:

```bash
.venv/bin/python first_judgment.py
```

## Read the answer

Expected output structure, not a fixed transcript:

```text
Probability of billing: <number between 0 and 1>
Resolved model: <resolved model identifier>
Input tokens: <reported token count, or None if absent>
```

Checkpoint: you received the named typed answer and metadata. Your probability
and token count can vary. A value near one supports “yes”; near zero supports
“no.” A value near the middle indicates more uncertainty between those outcomes.
It does not measure how much of the ticket concerns billing.

A successfully parsed answer is not proof of a correct classification.
The numeric value also does not decide what your application should do next.
You will choose an acceptance rule in the
[first-policy tutorial](first-policy.md), which runs without a service call.

## Recover from a failed checkpoint

- `ModuleNotFoundError` for judgevet: use `.venv/bin/python`, and repeat the
  install command with that same interpreter.
- `KeyError: 'JEV_API__KEY'`: supply and export the variable in the shell that
  runs the program. Do not paste the key into the file.
- An authentication error: check that the supplied key is valid for the service.
  Re-enter it through the hidden prompt rather than printing it for inspection.
- A transport or service error: check network access and the service's status.
  The example does not implement retries. Review errors before sharing them;
  arbitrary tracebacks are not guaranteed to redact secrets.

For exception types and retry guidance, use the [error reference](../reference/errors.md)
and [library handling recipe](../how-to/handle-errors.md).

For deeper meaning, read [judgment types](../explanation/judgments.md) and
[verification limits](../explanation/verification.md). For lookup, use the
[API reference](../reference/api.md) and [glossary](../reference/glossary.md).
