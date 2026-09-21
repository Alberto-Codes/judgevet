# py.typed Marker

## Purpose

The `py.typed` marker file signals to type checkers (PEP 561) that this package
provides inline type annotations. Without it, consumers of `judgevet` receive
`Any` for all types, defeating the library's core claim of being a **typed
client**.

## Verification

After building, confirm the marker is included:

```bash
uv build
python -c "import zipfile; print([n for n in zipfile.ZipFile(\"dist/judgevet-0.1.0-py3-none-any.whl\").namelist() if \"py.typed\" in n])"
```

Expected output:

```python
["judgevet/py.typed"]
```

## Implementation

The file `src/judgevet/py.typed` is an empty marker. The `pyproject.toml`
`[tool.uv_build]` section explicitly includes it in the wheel.

## Consumer check

A scratch venv can verify type resolution:

```bash
uv venv
uv pip install dist/judgevet-0.1.0-py3-none-any.whl
uv pip install ty
uv run ty check -c "from judgevet.domain.response import SystemOneResponse; x: SystemOneResponse"
```

If the marker is present, `ty` resolves `SystemOneResponse`. Without it, it
reports `Name not found`.
