# Changelog

## [0.1.0](https://github.com/Alberto-Codes/judgevet/compare/v0.0.1...v0.1.0) (2026-09-21)


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
