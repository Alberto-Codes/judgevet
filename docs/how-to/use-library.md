---
status: draft
---

# Call Jev from a synchronous Python program

Status: **draft**.

Use this recipe when a Python caller can wait for a judgment before continuing.
Install judgevet in that interpreter's environment. Configure an environment key, mounted file or
[credential command](../reference/configuration.md#credential-sources); the [first tutorial](../tutorials/first-judgment.md)
shows setup. The call needs service access and sends the supplied content.
Read [data disclosure](../../SECURITY.md#data-sent-to-the-service) first.

Save this complete program as `judge_ticket.py` and run it with your installed
Python interpreter:

```python
from judgevet import HTTPSystemOneAdapter, Noul, bind_request_id
from judgevet.adapters.inbound.logs import configure
from judgevet.adapters.inbound.settings import Settings

settings = Settings()
configure(settings.log)
key = settings.api.resolve_key()
if key is None:
    raise SystemExit("Configure a credential source before calling Jev")

with (
    HTTPSystemOneAdapter(
        api_key=key.get_secret_value(),
        base_url=settings.api.base_url,
        network=settings.api.network_config,
        retry=settings.api.retry_policy,
    ) as adapter,
    bind_request_id("request-123"),
):
    response = adapter.system_one(
        state="I was charged twice.",
        questions={"billing": Noul(instructions="Is this about billing?")},
        model="jev-1.13.0",
    )

print(response.nouls["billing"].noul)
```

Expected outcome: one probability between zero and one on stdout.
With `JEV_LOG__LEVEL=debug`, stderr also carries one terminal diagnostic with
request identifier `request-123`; supply your own non-sensitive identifier.
See the [event contract](../reference/events.md) for fields and scope lifetime. Its value
can vary. `nouls` selects typed Noul answers; use the name supplied in
`questions`. Noul semantics follow the [vendor definition](https://docs.typesafe.ai/primitives/noul).
A valid answer does not prove the classification is correct.

The context manager owns cleanup, including when a call raises. For several
calls, keep the adapter open around those calls and close it after the last
one. The returned values remain usable after closing. Direct constructors do
not read judgevet environment settings: this example explicitly reads Settings
and resolves one wrapped key before constructing the adapter. Leave `JEV_API__CA_BUNDLE` unset for normal HTTPX
trust roots. In a private-CA deployment, set it to your approved PEM bundle.
Certificate and hostname verification stay enabled. See
[network configuration](../reference/configuration.md#proxy-and-tls-configuration)
for proxy precedence and TLS limits.

For missing credentials, check the variable's presence without printing it.
For service failures, use [error handling](handle-errors.md). To produce a
local acceptance decision, follow the [policy workflow](use-policy-library.md).
Use the [async recipe](use-async-library.md) when your caller already uses async
I/O; see [supported imports](../reference/compatibility.md) for the contract.

## Supply ordered image evidence

Use `judgevet.media` with an application-owned `MediaSystemOnePort`. The
provider declares static capabilities for the selected model and implements
`system_one_media`. Judgevet supplies no image inference implementation.
The HTTP adapter has no media capability. CLI and MCP image exposure are
separate work.

This offline example constructs evidence without decoding its bytes:

```python
from judgevet.media import ImageAttachment, ImageEvidence, MediaCapabilities

image = ImageAttachment("scan", b"opaque-encoded-image", "image/png")
evidence = ImageEvidence([image], {"claim": ["scan"]}, required={"claim"})
capabilities = MediaCapabilities({"image/png"})
assert evidence.images[0].data == b"opaque-encoded-image"
assert evidence.by_question["claim"] == ("scan",)
assert capabilities.max_images == 16
```

Call `judge_with_images(port, state, questions, model, evidence=evidence)` with
your selected provider. Image IDs bind evidence to question IDs. The helper
preserves exact bytes, global image order and each question's reference order.
Sharing an image across questions is allowed. Constructors snapshot collections
and reject malformed associations with `ValueError`.

Unknown question references raise `ProviderRequestError`. Required questions
without attachments raise `MissingEvidenceError`, its subclass. Unsupported
formats or limits raise `ProviderCapabilityError` before inference. Allowed
formats are PNG, JPEG and WebP. Local ceilings are 16 images, 8 MiB per image
and 32 MiB total; a provider can lower these ceilings. Nonempty media never
falls back to text. Valid empty optional evidence calls the original text
operation without capability lookup or new answer checks.

The helper checks media answer IDs, variants and Choice labels, then returns
the provider's original response. Contract failures raise `ProviderResponseError`.
Declared transport failures retain their error class. An insufficient-evidence
answer is an ordinary Choice only when you declare that criterion yourself.
Existing policy rules determine its result. Provider numbers imply no measured
calibration; unknown usage remains `None` and zero remains zero. These are local
offline contracts, not evidence of a live model's image support or quality.
Source: [accepted media contract](https://github.com/Alberto-Codes/judgevet/issues/203#issuecomment-5851219798).

To attach media provenance to your existing audit record, import
`media_provenance` from `judgevet.media_audit`. Call it with your `ImageEvidence`,
question mapping and explicit nonempty bytes `fingerprint_key`. Pass the result
as `JudgmentRecord.media_provenance`, or add it through your existing audit sink.
Use opaque IDs and keep the key in application-owned secret storage. The helper
retains fingerprints and declared metadata, not image bytes or question text.
It does not write another record or account for provider attempts. See
[optional media provenance](../reference/configuration.md#optional-media-provenance)
for key rotation, equality leakage and metadata limits.
