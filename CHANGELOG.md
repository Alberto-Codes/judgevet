# Changelog

Maintained by [release-please](https://github.com/googleapis/release-please)
from conventional commit messages. Do not edit entries by hand.

## [0.11.0](https://github.com/Alberto-Codes/judgevet/compare/v0.10.2...v0.11.0) (2026-09-25)


### ⚠ BREAKING CHANGES

* Noul(instructions, criteria), Choice(criteria, instructions) and Score(criteria, instructions) no longer accept positional arguments. Name every argument: Noul(instructions=...), Choice(criteria=...), Score(criteria=...). Known callers: judgevet's own policy tests and doc-schema script, migrated here. Downstream callers that construct positionally must name the arguments before they upgrade.

### Features

* export VERIFIED_MODEL and keep it equal to the STATUS.md model ([1e8021c](https://github.com/Alberto-Codes/judgevet/commit/1e8021c4ab615cddc64ba7e80bab13e5832729de)), references [#173](https://github.com/Alberto-Codes/judgevet/issues/173)
* **testing:** ship FakeSystemOnePort and AsyncFakeSystemOnePort ([77587f4](https://github.com/Alberto-Codes/judgevet/commit/77587f4987bfff43abac4ce0ae887f6a8d5b19a9)), references [#171](https://github.com/Alberto-Codes/judgevet/issues/171)


### Refactoring

* make Noul, Choice and Score construction keyword-only ([33d0c36](https://github.com/Alberto-Codes/judgevet/commit/33d0c36edde93aeeabadb4e542c4ed802a4cb931)), references [#172](https://github.com/Alberto-Codes/judgevet/issues/172)


### Documentation

* **api:** document the accepted Choice criteria value forms ([3b38b42](https://github.com/Alberto-Codes/judgevet/commit/3b38b426ba735a53e66e7b99d5e0ef40f0ff8123)), references [#174](https://github.com/Alberto-Codes/judgevet/issues/174)

## [0.10.2](https://github.com/Alberto-Codes/judgevet/compare/v0.10.1...v0.10.2) (2026-09-25)


### Fixes

* reject nonfinite answers and normalize response errors ([37e8fab](https://github.com/Alberto-Codes/judgevet/commit/37e8fab447bd6deee364b2a1d12e5bf5a4ba6c3a)), references [#170](https://github.com/Alberto-Codes/judgevet/issues/170)
* scale the probability-sum tolerance with the number of levels ([eaea9b0](https://github.com/Alberto-Codes/judgevet/commit/eaea9b06075f92cce6c32882a4235117c2388a38)), references [#175](https://github.com/Alberto-Codes/judgevet/issues/175)


### Documentation

* add CI, licence, ruff and docvet badges to the README ([83a09f1](https://github.com/Alberto-Codes/judgevet/commit/83a09f120d67b9c36e87fbc361645c18383bfd30)), references [#45](https://github.com/Alberto-Codes/judgevet/issues/45)
* add the social preview card and decline Sonar ([9d49410](https://github.com/Alberto-Codes/judgevet/commit/9d4941004f7da14aafdce29ab389be0c9c2ad619)), references [#74](https://github.com/Alberto-Codes/judgevet/issues/74)
* record the Cursor CLI as a verified worker harness ([a20655e](https://github.com/Alberto-Codes/judgevet/commit/a20655e9883dbe283ba46860739f5844e470d31b)), references [#49](https://github.com/Alberto-Codes/judgevet/issues/49)
* record the vendor's service limits in the API reference ([bff03df](https://github.com/Alberto-Codes/judgevet/commit/bff03dfcf3747821f20955be0e144200dc03f393)), references [#39](https://github.com/Alberto-Codes/judgevet/issues/39)
* record verified 0.10.1 release and onboarding evidence ([70e0ceb](https://github.com/Alberto-Codes/judgevet/commit/70e0cebcc7a8e3a85af2c3fcb6850c88642dd4bb)), references [#165](https://github.com/Alberto-Codes/judgevet/issues/165)

## [0.10.1](https://github.com/Alberto-Codes/judgevet/compare/v0.10.0...v0.10.1) (2026-09-24)


### Fixes

* synchronize host recipe pins in release candidates ([2d95997](https://github.com/Alberto-Codes/judgevet/commit/2d95997e47aa4cb9fecd9986b46018201fa3ec3f)), references [#168](https://github.com/Alberto-Codes/judgevet/issues/168) [#165](https://github.com/Alberto-Codes/judgevet/issues/165)


### Documentation

* **mcp:** add host-native setup and credential recipes ([0dbad55](https://github.com/Alberto-Codes/judgevet/commit/0dbad5535e43d7d0ad2dd439913a35709d114836)), references [#163](https://github.com/Alberto-Codes/judgevet/issues/163) [#165](https://github.com/Alberto-Codes/judgevet/issues/165)
* record host onboarding survey and release scope ([d712af1](https://github.com/Alberto-Codes/judgevet/commit/d712af148fb1822387c5ed37b8f3ab353f5539e5)), references [#162](https://github.com/Alberto-Codes/judgevet/issues/162) [#165](https://github.com/Alberto-Codes/judgevet/issues/165) [#167](https://github.com/Alberto-Codes/judgevet/issues/167)
* record verified 0.10.0 release and registry listing ([0b09e97](https://github.com/Alberto-Codes/judgevet/commit/0b09e977c7e21040ae70ab266c4a14b75544adb0)), references [#65](https://github.com/Alberto-Codes/judgevet/issues/65) [#160](https://github.com/Alberto-Codes/judgevet/issues/160)
* state the repository contribution policy ([6b07e7c](https://github.com/Alberto-Codes/judgevet/commit/6b07e7ceb9ed9e3d1659e29227bb9b7cdfcd90b1)), references [#44](https://github.com/Alberto-Codes/judgevet/issues/44) [#165](https://github.com/Alberto-Codes/judgevet/issues/165)
* validate native host setup and record remaining limits ([7f92793](https://github.com/Alberto-Codes/judgevet/commit/7f9279378f97e9124c8e3605c499f929aa0f611f)), references [#164](https://github.com/Alberto-Codes/judgevet/issues/164) [#165](https://github.com/Alberto-Codes/judgevet/issues/165) [#167](https://github.com/Alberto-Codes/judgevet/issues/167)
* verify a credential-free contributor setup route ([baefc01](https://github.com/Alberto-Codes/judgevet/commit/baefc010912e8c184005a1883e85a0eb39f2dd18)), references [#21](https://github.com/Alberto-Codes/judgevet/issues/21) [#165](https://github.com/Alberto-Codes/judgevet/issues/165)

## [0.10.0](https://github.com/Alberto-Codes/judgevet/compare/v0.9.0...v0.10.0) (2026-09-24)


### Features

* **mcp:** add validated registry manifest and launcher checks ([403aea9](https://github.com/Alberto-Codes/judgevet/commit/403aea9bce905ec0d159117546373de12e5e2611)), references [#47](https://github.com/Alberto-Codes/judgevet/issues/47)


### Fixes

* **release:** render issue references without claiming closure ([f6b7737](https://github.com/Alberto-Codes/judgevet/commit/f6b773748a8d65a5b8ae1e48b3a39666f8bbfa20)), references [#125](https://github.com/Alberto-Codes/judgevet/issues/125) [#160](https://github.com/Alberto-Codes/judgevet/issues/160)


### Refactoring

* **mcp:** separate discovery and tool handlers ([7fa32b2](https://github.com/Alberto-Codes/judgevet/commit/7fa32b27dd2053471f06b83ae8cd771885781f82)), references [#80](https://github.com/Alberto-Codes/judgevet/issues/80)


### Documentation

* record verified 0.9.0 release and installation ([98cf8cd](https://github.com/Alberto-Codes/judgevet/commit/98cf8cd2ef74da448d15a69e4704fab2ff343d3c)), references [#157](https://github.com/Alberto-Codes/judgevet/issues/157)

## [0.9.0](https://github.com/Alberto-Codes/judgevet/compare/v0.8.0...v0.9.0) (2026-09-24)


### Features

* add caller-controlled state redaction before transmission ([4985677](https://github.com/Alberto-Codes/judgevet/commit/4985677abb66402df95cafb537f574117f034c37)), closes [#53](https://github.com/Alberto-Codes/judgevet/issues/53) [#157](https://github.com/Alberto-Codes/judgevet/issues/157)
* support explicit gateway authentication and metadata ([50133e2](https://github.com/Alberto-Codes/judgevet/commit/50133e255a508d709d46bb21e66a911c5e7bbea7)), closes [#63](https://github.com/Alberto-Codes/judgevet/issues/63) [#157](https://github.com/Alberto-Codes/judgevet/issues/157)


### Documentation

* record public gateway acceptance contract ([5d758b0](https://github.com/Alberto-Codes/judgevet/commit/5d758b02e80aba2711180543ac2c1d5986908f8c)), closes [#154](https://github.com/Alberto-Codes/judgevet/issues/154) [#157](https://github.com/Alberto-Codes/judgevet/issues/157)
* record verified 0.8.0 release and installation ([2bec6fe](https://github.com/Alberto-Codes/judgevet/commit/2bec6fe19ba67ffe6d76184a37f2d70061293e9f)), closes [#155](https://github.com/Alberto-Codes/judgevet/issues/155)

## [0.8.0](https://github.com/Alberto-Codes/judgevet/compare/v0.7.0...v0.8.0) (2026-09-23)


### Features

* **api:** add bounded opt-in retries across adapters ([a532cb2](https://github.com/Alberto-Codes/judgevet/commit/a532cb2ebd6cc977a09b930f3464c8c40ac3f4a0)), closes [#33](https://github.com/Alberto-Codes/judgevet/issues/33)
* **api:** add scoped correlation and diagnostic event contracts ([04b4c51](https://github.com/Alberto-Codes/judgevet/commit/04b4c5162dc97474ec92ce03665d159cbc6e8bb8)), closes [#64](https://github.com/Alberto-Codes/judgevet/issues/64)
* **api:** configure proxies and private CA trust ([e2f584b](https://github.com/Alberto-Codes/judgevet/commit/e2f584b22ce2af706880d9b902d88ea43471d8c4)), closes [#55](https://github.com/Alberto-Codes/judgevet/issues/55)
* **cli:** resolve file and command credential sources ([a5059d9](https://github.com/Alberto-Codes/judgevet/commit/a5059d9d21bc8e8139689de38f92acb963d687be)), closes [#61](https://github.com/Alberto-Codes/judgevet/issues/61)


### Fixes

* reject stale artifact directories before smoke builds ([ee4a30d](https://github.com/Alberto-Codes/judgevet/commit/ee4a30dd6fc973d7421d4eab215fd22942c1ae26)), closes [#153](https://github.com/Alberto-Codes/judgevet/issues/153) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)


### Refactoring

* **cli:** keep policy composition within the size limit ([bb592b6](https://github.com/Alberto-Codes/judgevet/commit/bb592b6fc35578268a269e5c72f45e3a5f04670f)), closes [#55](https://github.com/Alberto-Codes/judgevet/issues/55)


### Documentation

* add practical library CLI and MCP task guides ([273b94d](https://github.com/Alberto-Codes/judgevet/commit/273b94d09f735e171338aba4d06dc94876a7b57c)), closes [#150](https://github.com/Alberto-Codes/judgevet/issues/150) [#145](https://github.com/Alberto-Codes/judgevet/issues/145) [#10](https://github.com/Alberto-Codes/judgevet/issues/10)
* complete public API CLI MCP and policy reference ([c5897f3](https://github.com/Alberto-Codes/judgevet/commit/c5897f386d58ce2e278532d8e27aaa97aeb76046)), closes [#151](https://github.com/Alberto-Codes/judgevet/issues/151) [#145](https://github.com/Alberto-Codes/judgevet/issues/145) [#10](https://github.com/Alberto-Codes/judgevet/issues/10)
* define canonical judgment vocabulary ([4dbf542](https://github.com/Alberto-Codes/judgevet/commit/4dbf5428862f24200f243a6c61cd8cc1acb765cf)), closes [#46](https://github.com/Alberto-Codes/judgevet/issues/46) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* enforce contextual glossary terminology ([a4c48a6](https://github.com/Alberto-Codes/judgevet/commit/a4c48a6a3dc5004228551da1149eb284309a7bf0)), closes [#71](https://github.com/Alberto-Codes/judgevet/issues/71) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* enforce the local plain-English writing profile ([fd3237b](https://github.com/Alberto-Codes/judgevet/commit/fd3237b7c0632ccfc6be5991e82075b28b0cf61c)), closes [#70](https://github.com/Alberto-Codes/judgevet/issues/70) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* establish documentation navigation foundation ([49be1af](https://github.com/Alberto-Codes/judgevet/commit/49be1aff1bf521670f053db13f8dc40caa689009)), closes [#10](https://github.com/Alberto-Codes/judgevet/issues/10) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* explain container and serverless deployment ([41d0bb4](https://github.com/Alberto-Codes/judgevet/commit/41d0bb4f6e0ea53f25d1eca3f33745aae13d5e98)), closes [#58](https://github.com/Alberto-Codes/judgevet/issues/58)
* explain judgments policies and evidence limits ([0607bfe](https://github.com/Alberto-Codes/judgevet/commit/0607bfe5dee99cfd4e7398c92611f5f358d60f1a)), closes [#149](https://github.com/Alberto-Codes/judgevet/issues/149) [#145](https://github.com/Alberto-Codes/judgevet/issues/145) [#10](https://github.com/Alberto-Codes/judgevet/issues/10)
* explain library-first architecture and ownership ([f9ff8ed](https://github.com/Alberto-Codes/judgevet/commit/f9ff8ed954e017bf57c7197a99074e354edb4a35)), closes [#11](https://github.com/Alberto-Codes/judgevet/issues/11) [#145](https://github.com/Alberto-Codes/judgevet/issues/145) [#10](https://github.com/Alberto-Codes/judgevet/issues/10)
* finish navigation and trust-status audit ([b37a7dc](https://github.com/Alberto-Codes/judgevet/commit/b37a7dc2f6546f4f033eda8efba388edd29130d9)), closes [#10](https://github.com/Alberto-Codes/judgevet/issues/10) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* gate strict site builds and reference integrity ([64e4489](https://github.com/Alberto-Codes/judgevet/commit/64e44899ccfee44ef81e604bf9e60f4e4954ec35)), closes [#12](https://github.com/Alberto-Codes/judgevet/issues/12) [#10](https://github.com/Alberto-Codes/judgevet/issues/10) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* illustrate call flow and data disclosure boundaries ([77a050a](https://github.com/Alberto-Codes/judgevet/commit/77a050a484861024d36b3c370179b40b54923a88)), closes [#73](https://github.com/Alberto-Codes/judgevet/issues/73) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* lead README with one typed judgment journey ([2d79dd0](https://github.com/Alberto-Codes/judgevet/commit/2d79dd009112a63dc2c5abd607bf5300fef612e9)), closes [#152](https://github.com/Alberto-Codes/judgevet/issues/152) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* link the verified public documentation site ([6c90e7f](https://github.com/Alberto-Codes/judgevet/commit/6c90e7fc868ad519690672077dfaa7051891e360)), closes [#41](https://github.com/Alberto-Codes/judgevet/issues/41)
* record final documentation program verification ([3517e3e](https://github.com/Alberto-Codes/judgevet/commit/3517e3e8d5d432433eb613e17a845746bf05ae79)), closes [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* record verified 0.7.0 release and installation ([61212f3](https://github.com/Alberto-Codes/judgevet/commit/61212f321f6c8ac4df083e6aae1e4860ee7edf17)), closes [#143](https://github.com/Alberto-Codes/judgevet/issues/143) [#138](https://github.com/Alberto-Codes/judgevet/issues/138)
* reference configuration and error contracts ([9053fc8](https://github.com/Alberto-Codes/judgevet/commit/9053fc8ef9ae2f708688ff989c2641a713917c97)), closes [#151](https://github.com/Alberto-Codes/judgevet/issues/151) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* repair API examples and artifact verification ([b32afa2](https://github.com/Alberto-Codes/judgevet/commit/b32afa2ab6d3e5b3d8a86cd816ba93d67c0f73b9)), closes [#146](https://github.com/Alberto-Codes/judgevet/issues/146) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* separate user guidance from maintainer records ([e96b024](https://github.com/Alberto-Codes/judgevet/commit/e96b02414266b3d72895cead8caf927db5e89306)), closes [#147](https://github.com/Alberto-Codes/judgevet/issues/147) [#145](https://github.com/Alberto-Codes/judgevet/issues/145)
* teach first judgment and local policy decisions ([fb0169f](https://github.com/Alberto-Codes/judgevet/commit/fb0169fc05a19a9bde80853e3e3259724ca29c0e)), closes [#148](https://github.com/Alberto-Codes/judgevet/issues/148) [#149](https://github.com/Alberto-Codes/judgevet/issues/149) [#145](https://github.com/Alberto-Codes/judgevet/issues/145) [#10](https://github.com/Alberto-Codes/judgevet/issues/10)

## [0.7.0](https://github.com/Alberto-Codes/judgevet/compare/v0.6.0...v0.7.0) (2026-09-23)


### Features

* **api:** add immutable typed policy validation and evaluation ([a7069ca](https://github.com/Alberto-Codes/judgevet/commit/a7069ca5d53cc74a6c0ffc76ddf7f5df6f302f42)), closes [#140](https://github.com/Alberto-Codes/judgevet/issues/140)
* **api:** support public ports, answers and Jev errors ([bef1152](https://github.com/Alberto-Codes/judgevet/commit/bef1152e7493a8603090f64729a4a10cc7e02a33)), closes [#139](https://github.com/Alberto-Codes/judgevet/issues/139)
* **cli:** share typed policy decoding and comparisons ([c64ac1d](https://github.com/Alberto-Codes/judgevet/commit/c64ac1d931a844b9ee226ab35133b089c75deca7)), closes [#141](https://github.com/Alberto-Codes/judgevet/issues/141)


### Documentation

* **api:** document policy use and surface compatibility ([256d4cc](https://github.com/Alberto-Codes/judgevet/commit/256d4cc6871714f75a1b328a59ca7e26b224ebeb)), closes [#142](https://github.com/Alberto-Codes/judgevet/issues/142)
* document credentials and security reporting ([c70dfd5](https://github.com/Alberto-Codes/judgevet/commit/c70dfd5e8cbc0639ad9ee24a657b17a1b785f906)), closes [#14](https://github.com/Alberto-Codes/judgevet/issues/14)
* introduce the verified 0.6.0 public workflows ([0ec30a8](https://github.com/Alberto-Codes/judgevet/commit/0ec30a80a9cf95a569de50cdc7d0a9b1631636ea)), closes [#43](https://github.com/Alberto-Codes/judgevet/issues/43)
* record verified 0.6.0 release and installation ([44ee39d](https://github.com/Alberto-Codes/judgevet/commit/44ee39d3f8e16c34d6b3748d4c40405dc41bfc98))
* state the 0.6.0 cryptographic posture ([20e4969](https://github.com/Alberto-Codes/judgevet/commit/20e4969890d223b859a3e0fa4784c553e137fdf0)), closes [#62](https://github.com/Alberto-Codes/judgevet/issues/62)

## [0.6.0](https://github.com/Alberto-Codes/judgevet/compare/v0.5.0...v0.6.0) (2026-09-23)


### Features

* **logging:** wire safe diagnostics at composition roots ([d763313](https://github.com/Alberto-Codes/judgevet/commit/d76331349ad82f12d741d518b186c493b693a7b2)), closes [#27](https://github.com/Alberto-Codes/judgevet/issues/27) [#3](https://github.com/Alberto-Codes/judgevet/issues/3)


### Fixes

* **ci:** require release environment credentials and identity ([70ca8ab](https://github.com/Alberto-Codes/judgevet/commit/70ca8abe7a180ef1e25335690013c03ac6ef4eb9)), closes [#102](https://github.com/Alberto-Codes/judgevet/issues/102)
* **cli:** handle rate limits in both command paths ([1f336bc](https://github.com/Alberto-Codes/judgevet/commit/1f336bcd8c934ae31e4350b98765fe494170702d)), closes [#135](https://github.com/Alberto-Codes/judgevet/issues/135)
* **http:** validate error detail shapes before rendering ([081aec0](https://github.com/Alberto-Codes/judgevet/commit/081aec0f7f3a5e8513370d290d0d81b77050518e)), closes [#136](https://github.com/Alberto-Codes/judgevet/issues/136)
* **smoke:** preserve safe failure stages through cleanup ([fd96bab](https://github.com/Alberto-Codes/judgevet/commit/fd96babe011f1b6a99aee0b5ce92e0d0f21622c3)), closes [#133](https://github.com/Alberto-Codes/judgevet/issues/133)


### Documentation

* record policy API and compatibility decisions ([82f17c3](https://github.com/Alberto-Codes/judgevet/commit/82f17c3a61a87bbaabcb2c7b5a82cb918544060f)), closes [#67](https://github.com/Alberto-Codes/judgevet/issues/67) [#66](https://github.com/Alberto-Codes/judgevet/issues/66)
* record verified 0.5.0 release and developer workflow ([4f71f04](https://github.com/Alberto-Codes/judgevet/commit/4f71f04cbc20a00263ce35370ccde40a333ee9ad)), closes [#130](https://github.com/Alberto-Codes/judgevet/issues/130) [#131](https://github.com/Alberto-Codes/judgevet/issues/131) [#133](https://github.com/Alberto-Codes/judgevet/issues/133)
* record verified release credential scope ([12d1fce](https://github.com/Alberto-Codes/judgevet/commit/12d1fcedb4f2536e7b51edf743ff501f93e8fadd)), closes [#102](https://github.com/Alberto-Codes/judgevet/issues/102)

## [0.5.0](https://github.com/Alberto-Codes/judgevet/compare/v0.4.1...v0.5.0) (2026-09-22)


### Features

* **cli:** evaluate explicit acceptance policies ([610ed95](https://github.com/Alberto-Codes/judgevet/commit/610ed95e84e2023ce6f7b741a22a9f98ed50faf6)), closes [#128](https://github.com/Alberto-Codes/judgevet/issues/128) [#131](https://github.com/Alberto-Codes/judgevet/issues/131)
* **cli:** load reusable questions and explicit state sources ([59218ec](https://github.com/Alberto-Codes/judgevet/commit/59218ec03dc10776bdfa3b361a677e0f5fc6bbd9)), closes [#127](https://github.com/Alberto-Codes/judgevet/issues/127) [#68](https://github.com/Alberto-Codes/judgevet/issues/68) [#131](https://github.com/Alberto-Codes/judgevet/issues/131)


### Documentation

* **cli:** ship an opt-in staged-diff review example ([d8105db](https://github.com/Alberto-Codes/judgevet/commit/d8105dbff34a67be1a6cfe07bbbc8ce0e4b8ac5d)), closes [#129](https://github.com/Alberto-Codes/judgevet/issues/129) [#131](https://github.com/Alberto-Codes/judgevet/issues/131)
* record verified 0.4.1 release and installation ([d6a12f1](https://github.com/Alberto-Codes/judgevet/commit/d6a12f15173706cee7c380d8a57442684b5bf893)), closes [#124](https://github.com/Alberto-Codes/judgevet/issues/124)

## [0.4.1](https://github.com/Alberto-Codes/judgevet/compare/v0.4.0...v0.4.1) (2026-09-22)


### Fixes

* **cli:** propagate handled failures to installed command exit status ([97fff00](https://github.com/Alberto-Codes/judgevet/commit/97fff00d00402778d491033c67c69c170faa733d)), closes [#123](https://github.com/Alberto-Codes/judgevet/issues/123) [#124](https://github.com/Alberto-Codes/judgevet/issues/124)


### Documentation

* reconcile backlog acceptance after 0.4.0 ([5f2c346](https://github.com/Alberto-Codes/judgevet/commit/5f2c34622febb2c0dfc3804a1a0c5f268f4b3068)), closes [#34](https://github.com/Alberto-Codes/judgevet/issues/34) [#22](https://github.com/Alberto-Codes/judgevet/issues/22) [#19](https://github.com/Alberto-Codes/judgevet/issues/19) [#3](https://github.com/Alberto-Codes/judgevet/issues/3) [#27](https://github.com/Alberto-Codes/judgevet/issues/27) [#43](https://github.com/Alberto-Codes/judgevet/issues/43) [#67](https://github.com/Alberto-Codes/judgevet/issues/67) [#68](https://github.com/Alberto-Codes/judgevet/issues/68) [#8](https://github.com/Alberto-Codes/judgevet/issues/8) [#124](https://github.com/Alberto-Codes/judgevet/issues/124)
* record verified 0.4.0 release and installation ([0290d9f](https://github.com/Alberto-Codes/judgevet/commit/0290d9fa9318124ad8530e8bc710c94f295c13df)), closes [#121](https://github.com/Alberto-Codes/judgevet/issues/121)

## [0.4.0](https://github.com/Alberto-Codes/judgevet/compare/v0.3.0...v0.4.0) (2026-09-22)


### Features

* add typed answer accessors to responses ([4362721](https://github.com/Alberto-Codes/judgevet/commit/4362721accd400405bd01f992de0b52c76dbeec2)), closes [#103](https://github.com/Alberto-Codes/judgevet/issues/103) [#121](https://github.com/Alberto-Codes/judgevet/issues/121)


### Fixes

* **cli:** separate public help from developer docstrings ([a4bfafa](https://github.com/Alberto-Codes/judgevet/commit/a4bfafa403357656cb315b662ff2501b8b076ad5)), closes [#16](https://github.com/Alberto-Codes/judgevet/issues/16) [#121](https://github.com/Alberto-Codes/judgevet/issues/121)


### Documentation

* record verified 0.3.0 installation and release ([2aae183](https://github.com/Alberto-Codes/judgevet/commit/2aae18309241b69595fb79e3f7eb65e64cd1236b)), closes [#119](https://github.com/Alberto-Codes/judgevet/issues/119) [#115](https://github.com/Alberto-Codes/judgevet/issues/115) [#116](https://github.com/Alberto-Codes/judgevet/issues/116)
* record verified optional assisted audit ([cd79dd0](https://github.com/Alberto-Codes/judgevet/commit/cd79dd06bacd8aac10468957b19d173cf858af42)), closes [#97](https://github.com/Alberto-Codes/judgevet/issues/97) [#121](https://github.com/Alberto-Codes/judgevet/issues/121)

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
