# Changelog

Maintained by [release-please](https://github.com/googleapis/release-please)
from conventional commit messages. Do not edit entries by hand.

## [0.3.0](https://github.com/Alberto-Codes/judgevet/compare/v0.2.0...v0.3.0) (2026-09-22)


### Features

* **mcp:** ship the supported stdio command ([f94dc70](https://github.com/Alberto-Codes/judgevet/commit/f94dc7028da5d3b38b51191b40763f5b203aa5c7)), closes [#25](https://github.com/Alberto-Codes/judgevet/issues/25)


### Fixes

* **gates:** detect ty suppressions and remove existing uses ([d6fce1c](https://github.com/Alberto-Codes/judgevet/commit/d6fce1cb905cbf67818c2bd1d5ae82e8d804585d)), closes [#111](https://github.com/Alberto-Codes/judgevet/issues/111)
* **mcp:** advertise the installed distribution version ([e70da9b](https://github.com/Alberto-Codes/judgevet/commit/e70da9b4ef2a766dfbd5bad6faea357f6615646c)), closes [#113](https://github.com/Alberto-Codes/judgevet/issues/113)
* recognize interpreter install roots in release smoke ([fbb19fd](https://github.com/Alberto-Codes/judgevet/commit/fbb19fd4a7fc218a8ba9408b36c021447d7adabd)), closes [#118](https://github.com/Alberto-Codes/judgevet/issues/118) [#115](https://github.com/Alberto-Codes/judgevet/issues/115) [#116](https://github.com/Alberto-Codes/judgevet/issues/116)


### Documentation

* correct the official SDK comparison ([85ed059](https://github.com/Alberto-Codes/judgevet/commit/85ed059d4b12f21c0ed323ce4a1298cc6c9226b5)), closes [#104](https://github.com/Alberto-Codes/judgevet/issues/104)
* document candidate and index release verification ([8b46302](https://github.com/Alberto-Codes/judgevet/commit/8b46302c15a6fef87c4a986e514f8688278d21b1)), closes [#117](https://github.com/Alberto-Codes/judgevet/issues/117) [#116](https://github.com/Alberto-Codes/judgevet/issues/116)
* explain verified installs and source MCP setup ([cd3514c](https://github.com/Alberto-Codes/judgevet/commit/cd3514c61927a3fb89cb764a48fc7da4930ea871)), closes [#37](https://github.com/Alberto-Codes/judgevet/issues/37)
* **mcp:** distinguish tested initialization from SDK compatibility ([8d7afde](https://github.com/Alberto-Codes/judgevet/commit/8d7afde607c6d2997a3b6f13d4f71554e3e0a0c8)), closes [#114](https://github.com/Alberto-Codes/judgevet/issues/114)
* **release:** record rejected MCP artifact in Actions ([c42ab96](https://github.com/Alberto-Codes/judgevet/commit/c42ab96cbad29a6d30266c1817a62a16c3ff3109)), closes [#115](https://github.com/Alberto-Codes/judgevet/issues/115) [#116](https://github.com/Alberto-Codes/judgevet/issues/116)
* **release:** record verified 0.2.0 publication and artifact gate ([9725035](https://github.com/Alberto-Codes/judgevet/commit/9725035479b032ac145fecc3efedddefa24c11e6)), closes [#101](https://github.com/Alberto-Codes/judgevet/issues/101)

## [0.2.0](https://github.com/Alberto-Codes/judgevet/compare/v0.1.0...v0.2.0) (2026-09-22)


### Features

* export the async adapter from the package root ([14ba30a](https://github.com/Alberto-Codes/judgevet/commit/14ba30a7cbebc9b005c4bdd73e4ffbbd96d78200))
* **gate:** refuse a commit from an author this repository does not know ([2ec221c](https://github.com/Alberto-Codes/judgevet/commit/2ec221c570800c2631a622d72977f69aa7133b4d)), closes [#90](https://github.com/Alberto-Codes/judgevet/issues/90)
* **gates:** a gate reads the runtime dependency list ([028d27d](https://github.com/Alberto-Codes/judgevet/commit/028d27d94ac70cf52614faccaf1361827c0b266e))
* **gates:** catch a requirement naming an extra nobody publishes ([a0a72bb](https://github.com/Alberto-Codes/judgevet/commit/a0a72bbac349dcc08fce6f8429ed879366630068))
* **http:** an async outbound adapter and its port ([d6a64ea](https://github.com/Alberto-Codes/judgevet/commit/d6a64eac3add85f507ccc0f0ca106c7787139db4))
* **smoke:** run the built artifact, outside this checkout ([ed9df97](https://github.com/Alberto-Codes/judgevet/commit/ed9df974d4aa213feb74a765d5641a8c0e9da1ea))
* **tests:** redact the API key from pytest reports ([2e1ab1f](https://github.com/Alberto-Codes/judgevet/commit/2e1ab1f08d167ff5b142c93d39c76d4123e77210))


### Fixes

* **ci:** test-publish cannot use an index name, it has no checkout ([a84c1a1](https://github.com/Alberto-Codes/judgevet/commit/a84c1a15ac9f46f90fb39b0744faa55a3fafb7cb)), closes [#101](https://github.com/Alberto-Codes/judgevet/issues/101)
* **ci:** test-publish passed two mutually exclusive uv flags ([d314611](https://github.com/Alberto-Codes/judgevet/commit/d314611d3f59ddc770b5269e46c8f48a074d193a)), closes [#101](https://github.com/Alberto-Codes/judgevet/issues/101)
* **domain:** a noul's criteria keys are true and false, not yes and no ([d5fc98a](https://github.com/Alberto-Codes/judgevet/commit/d5fc98a6fc53967706154443a572ec0ced35a89a))
* **gate:** read the recorded author in range mode, not the pending one ([5d893fb](https://github.com/Alberto-Codes/judgevet/commit/5d893fb475f7fbbe7fc5977d00d1c1dc81cd7243)), closes [#90](https://github.com/Alberto-Codes/judgevet/issues/90)
* **gates:** the suppression gate reads scripts/, and reads comments ([28f61e0](https://github.com/Alberto-Codes/judgevet/commit/28f61e00f44e476ca1df7e8d653bd733909e1145))
* **gate:** the release PR's own commits are release-please's, not a human's ([a866ac2](https://github.com/Alberto-Codes/judgevet/commit/a866ac246eb7d4ed302e9c45f542792ee888f4ea)), closes [#90](https://github.com/Alberto-Codes/judgevet/issues/90)
* **http:** convert the documented question types to wire dicts ([bee1a09](https://github.com/Alberto-Codes/judgevet/commit/bee1a097b0f44c8a1687b25f88caa4fa2d2e1827))
* **smoke:** execute valid examples after layout findings ([0db29a3](https://github.com/Alberto-Codes/judgevet/commit/0db29a3e3010c5fc2e7b2f1ac8c70ded64394de3)), closes [#107](https://github.com/Alberto-Codes/judgevet/issues/107)
* **status:** correct a test count I typed instead of measured ([78e2742](https://github.com/Alberto-Codes/judgevet/commit/78e2742c1ba24551a672defa23ede6519fa311e0))


### Refactoring

* **http:** extract the sync-independent half of system_one ([90b5482](https://github.com/Alberto-Codes/judgevet/commit/90b5482002c069816dc6d4aba490c0d9a6a3fc44))


### Documentation

* delete NEXT_PROMPT.md, keep what it knew ([8dacf40](https://github.com/Alberto-Codes/judgevet/commit/8dacf400ec959d5ee1320b30f7afd0fd13522a58))
* **readme:** stop the PyPI page announcing itself as a draft ([e60962d](https://github.com/Alberto-Codes/judgevet/commit/e60962d8e19cd5ecaf653f0fad9c638e552d1ae2))
* record that 0.1.0 shipped ([c75549b](https://github.com/Alberto-Codes/judgevet/commit/c75549bba6370f82d388ad210c7d0a926eabf2bd)), closes [#88](https://github.com/Alberto-Codes/judgevet/issues/88)
* **release:** record the standing permission and the bar for using it ([1da21da](https://github.com/Alberto-Codes/judgevet/commit/1da21da64acfb2da43f8edb4c53097b6fa6a0a77))
* **status:** record the test-hygiene gate ([85df678](https://github.com/Alberto-Codes/judgevet/commit/85df67894326f960113bf9d9426ea7500e658e9d))
* **status:** refresh the facts that went stale ([e8fa42e](https://github.com/Alberto-Codes/judgevet/commit/e8fa42e5820998b56633b659a188995be32ad03a))
* **status:** the 3xx fallthrough is pinned now ([16ef80b](https://github.com/Alberto-Codes/judgevet/commit/16ef80b827c593a23482e4a8367954cb285c9865))
* **status:** the smoke test's two detectors do not detect ([dd130b7](https://github.com/Alberto-Codes/judgevet/commit/dd130b798bcf678571dcbbed3c61ce137f7cbbde)), closes [#106](https://github.com/Alberto-Codes/judgevet/issues/106)

## [0.1.0](https://github.com/Alberto-Codes/judgevet/compare/v0.0.1...v0.1.0) (2026-09-21)

**The first release of this library.** `0.0.1` on PyPI was a name reservation
carrying no working code, so the comparison link above has no tag to resolve
against and the "breaking changes" below broke nothing that had shipped — they
are recorded because the commits declared them during development, and because
anyone who installed from the repository before today will meet them.

What is worth knowing before you install:

- The domain model is **verified in part**. The success response shape and the
  401 and 422 error bodies were checked against the live service on
  2026-09-21. The 429 and 529 bodies have never been observed, one model has
  been exercised, and everything else is inferred from published
  documentation. `STATUS.md` holds the line-by-line table.
- Errors carry a `detail` that is **polymorphic** — an object for
  authentication failures, an array for validation failures. The adapter
  handles both and deliberately drops the `input` key, which echoes your
  request payload back.

### ⚠ BREAKING CHANGES

* **http:** requests that previously failed after five seconds now have thirty. Callers relying on a fast failure should set JEV_API__TIMEOUT_SECONDS.
* **domain:** constructing an answer with an out-of-range value, a probability map that is not a distribution, or a choice absent from that map now raises ValueError instead of succeeding. Assigning to a constructed answer raises. Callers that relied on building malformed answers must stop.
* rename the project to judgevet

### Features

* domain error types so httpx does not reach callers ([e0b71d4](https://github.com/Alberto-Codes/judgevet/commit/e0b71d4b0a6a204a83dbcbe56947e35908bd2ff4)), closes [#15](https://github.com/Alberto-Codes/judgevet/issues/15)
* **http:** surface the error detail, without the payload it carries ([0922a32](https://github.com/Alberto-Codes/judgevet/commit/0922a32cf41d2f3883f09c5276d6359debb2ae73)), closes [#85](https://github.com/Alberto-Codes/judgevet/issues/85)
* **mcp:** a stdio server exposing ask_noul ([33a600d](https://github.com/Alberto-Codes/judgevet/commit/33a600d55d8ca6f0db6f838862e6c8b7834e9bba)), closes [#23](https://github.com/Alberto-Codes/judgevet/issues/23)
* **mcp:** add ask_choice and ask_score tools ([2a785ee](https://github.com/Alberto-Codes/judgevet/commit/2a785ee6a5af6f00b7b04d03a6dbce23ed51abe5)), closes [#24](https://github.com/Alberto-Codes/judgevet/issues/24)
* one Settings for the whole client ([fb49388](https://github.com/Alberto-Codes/judgevet/commit/fb49388958337f87defb4fc3fc8a8af13f46a7be)), closes [#2](https://github.com/Alberto-Codes/judgevet/issues/2)
* port the CLI from argparse to typer ([5a8f311](https://github.com/Alberto-Codes/judgevet/commit/5a8f3111609143933f0d00f0496d6bd476df42d2)), closes [#1](https://github.com/Alberto-Codes/judgevet/issues/1)
* structured logging, configured once and redacting secrets ([4367256](https://github.com/Alberto-Codes/judgevet/commit/4367256886072ce62faeba3dbe6a258ceb6b4125)), closes [#26](https://github.com/Alberto-Codes/judgevet/issues/26)


### Fixes

* 429 is retryable and no longer reads as a bad request ([1f1fcb0](https://github.com/Alberto-Codes/judgevet/commit/1f1fcb0edf60ed84e08dcdba30f1f51a99d932a5)), closes [#18](https://github.com/Alberto-Codes/judgevet/issues/18)
* bring the ported core to green and gate the suppressions ([9a903e3](https://github.com/Alberto-Codes/judgevet/commit/9a903e307bbeb11653aafc34e77979f959f9a983)), closes [#7](https://github.com/Alberto-Codes/judgevet/issues/7)
* **domain:** enforce the invariants the types only implied ([5219e74](https://github.com/Alberto-Codes/judgevet/commit/5219e74c17707ec4330d193b2253a4c4c693c72e)), closes [#77](https://github.com/Alberto-Codes/judgevet/issues/77)
* **gate:** count suppression codes, not the patterns they sit under ([e5663e6](https://github.com/Alberto-Codes/judgevet/commit/e5663e60e562c9c033d1dc868427460f9275e1f0)), closes [#79](https://github.com/Alberto-Codes/judgevet/issues/79)
* **http:** raise the read budget, and stop connect inheriting it ([c361a10](https://github.com/Alberto-Codes/judgevet/commit/c361a105c2d944b59c65c958db882d39ae6557b5)), closes [#32](https://github.com/Alberto-Codes/judgevet/issues/32)
* **probe:** serialize the frozen domain, and record what the service returns ([c898fb2](https://github.com/Alberto-Codes/judgevet/commit/c898fb2af22e987f650cced524d9b97e63cf2bc6))
* refuse a plaintext base_url, which leaked the API key ([e48f88e](https://github.com/Alberto-Codes/judgevet/commit/e48f88e5bae7d1158e04636936463b2acb1b589d)), closes [#60](https://github.com/Alberto-Codes/judgevet/issues/60)
* ship py.typed so consumers actually get the types ([5765ac3](https://github.com/Alberto-Codes/judgevet/commit/5765ac31f2cbd00f3f73f225b8d460e7e183821d)), closes [#31](https://github.com/Alberto-Codes/judgevet/issues/31)


### Refactoring

* **cli:** type the composition root against the port ([51e7839](https://github.com/Alberto-Codes/judgevet/commit/51e7839e95e1782dbea380144f84fad6bc12e694)), closes [#81](https://github.com/Alberto-Codes/judgevet/issues/81)
* **http:** inject the transport, and move the CLI unit tests out of contract ([8254f63](https://github.com/Alberto-Codes/judgevet/commit/8254f633e439a1155567c0847053df834409eb33)), closes [#76](https://github.com/Alberto-Codes/judgevet/issues/76)
* move the typed boundary to the port ([038deb3](https://github.com/Alberto-Codes/judgevet/commit/038deb31ff03abd8f3f5ffabe34394a2c7d0d8ac)), closes [#17](https://github.com/Alberto-Codes/judgevet/issues/17)
* **ports:** make SystemOnePort a Protocol so adapters need no lineage ([47a7571](https://github.com/Alberto-Codes/judgevet/commit/47a75714040afc334c3c383b437f5609843d2802)), closes [#75](https://github.com/Alberto-Codes/judgevet/issues/75)
* rename the project to judgevet ([56ea823](https://github.com/Alberto-Codes/judgevet/commit/56ea82364a9f2e74f4e0fe8c2492f1ebc8819cf5))


### Documentation

* **adapters:** describe the three adapter packages, one of them correctly ([aabfaa3](https://github.com/Alberto-Codes/judgevet/commit/aabfaa3cde7827fa55ef26c0d40e3189c0ed8b0f))
* add the agent conventions and the hand-off ([05baf3a](https://github.com/Alberto-Codes/judgevet/commit/05baf3a6b50ab35826559c2e278a4b991ad27a45))
* cite the vendor's own reference, not five-day-old blogs ([7be6e18](https://github.com/Alberto-Codes/judgevet/commit/7be6e18359b8a9db4d35bd45107bb8dcfcb29da5)), closes [#20](https://github.com/Alberto-Codes/judgevet/issues/20)
* name the specifying model, and forbid destroying others' work ([4ac909a](https://github.com/Alberto-Codes/judgevet/commit/4ac909add94895ecac7da7d8fa6cd44a451e0d22)), closes [#82](https://github.com/Alberto-Codes/judgevet/issues/82)
* promote off sketch, for the parts a call actually exercised ([49cd61b](https://github.com/Alberto-Codes/judgevet/commit/49cd61b76a00b80540b2c534f6eb55ec19652bb7)), closes [#6](https://github.com/Alberto-Codes/judgevet/issues/6)
* refresh STATUS and record the rules the sessions earned ([689189b](https://github.com/Alberto-Codes/judgevet/commit/689189b8d75adcf4413d89292046f80fa60d8eb0)), closes [#28](https://github.com/Alberto-Codes/judgevet/issues/28)
* refresh the test count after the contract, invariant and gate work ([11a5c34](https://github.com/Alberto-Codes/judgevet/commit/11a5c34ebf8c5ec282c9381d9fc70f9dfd32fd4a))
* say how a commit closes its issue, not just that it references one ([6e11a41](https://github.com/Alberto-Codes/judgevet/commit/6e11a41f71de6ed8ae57588f53a696eef5c3a236)), closes [#79](https://github.com/Alberto-Codes/judgevet/issues/79)
