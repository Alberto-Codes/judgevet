---
status: draft
---

# py.typed marker

judgevet includes `judgevet/py.typed` to declare inline typing support under
[PEP 561](https://peps.python.org/pep-0561/). A type checker can use the installed
annotations. The marker does not prove that every caller is type-correct.

Package maintainers can [verify the wheel and an isolated typed consumer](../maintainers/verify-package.md).
Library callers can look up [supported imports](compatibility.md).
