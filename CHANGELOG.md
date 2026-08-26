# Changelog

## [1.6.0](https://github.com/runpod-workers/flash/compare/v1.5.0...v1.6.0) (2026-08-20)


### Features

* SLS-360 import shipped local modules before executing user code ([#100](https://github.com/runpod-workers/flash/issues/100)) ([a44da63](https://github.com/runpod-workers/flash/commit/a44da63664b14d70315a2b566e865a71f33f19aa))


### Bug Fixes

* **ci:** support py3.10 in check_git_deps import ([#106](https://github.com/runpod-workers/flash/issues/106)) ([89eb6a0](https://github.com/runpod-workers/flash/commit/89eb6a009e9ce0a4ecfc96c9e46ed0d3e4adf49e))
* **deps:** bump ([#105](https://github.com/runpod-workers/flash/issues/105)) ([ea9f7df](https://github.com/runpod-workers/flash/commit/ea9f7df2b424a507119a229c3be5d45041c92742))
* **deps:** bump runpod-flash 1.16.0 -&gt; 1.17.0, runpod 1.9.0 -&gt; 1.9.1 ([#99](https://github.com/runpod-workers/flash/issues/99)) ([7fb0d11](https://github.com/runpod-workers/flash/commit/7fb0d117e5ebd5ea27908a246699e6b6f0cc645d))
* **docker:** install torchvision in GPU worker image ([#101](https://github.com/runpod-workers/flash/issues/101)) ([53aeb8a](https://github.com/runpod-workers/flash/commit/53aeb8acc85dcbdf81b0e9a4d2e2ccbc8819999d))
* unpin runpod-flash to released 1.19.0 ([#103](https://github.com/runpod-workers/flash/issues/103)) ([cb76157](https://github.com/runpod-workers/flash/commit/cb76157b82861f1bd5b24f9953aa4b13a0d23fd0))

## [1.5.0](https://github.com/runpod-workers/flash/compare/v1.4.4...v1.5.0) (2026-04-29)


### Features

* multi-Python worker images with startup version check (AE-2827) ([#89](https://github.com/runpod-workers/flash/issues/89)) ([fa6bab9](https://github.com/runpod-workers/flash/commit/fa6bab9e4cbde2adf6df93655d0da948a11c15b9))


### Bug Fixes

* **deps:** bump runpod-flash 1.15.0 -&gt; 1.16.0 ([#95](https://github.com/runpod-workers/flash/issues/95)) ([f29eadd](https://github.com/runpod-workers/flash/commit/f29eadd3dfbca6c1621caf6a37a6204dafec71ca))

## [1.4.4](https://github.com/runpod-workers/flash/compare/v1.4.3...v1.4.4) (2026-04-27)


### Bug Fixes

* **deps:** bump runpod-flash 1.14.0 -&gt; 1.15.0 ([#92](https://github.com/runpod-workers/flash/issues/92)) ([65fabf7](https://github.com/runpod-workers/flash/commit/65fabf79203a43c2f5c9777a9bdd15bc07a3b8a0))

## [1.4.3](https://github.com/runpod-workers/flash/compare/v1.4.2...v1.4.3) (2026-04-22)


### Bug Fixes

* **deps:** bump runpod-flash 1.13.0 -&gt; 1.14.0 ([#90](https://github.com/runpod-workers/flash/issues/90)) ([f4ebebb](https://github.com/runpod-workers/flash/commit/f4ebebbdb5899ed0fadb94beba82c10b9b03a933))

## [1.4.2](https://github.com/runpod-workers/flash/compare/v1.4.1...v1.4.2) (2026-04-15)


### Bug Fixes

* **deps:** bump runpod-flash 1.11.3 -&gt; 1.13.0 ([#87](https://github.com/runpod-workers/flash/issues/87)) ([146ee6d](https://github.com/runpod-workers/flash/commit/146ee6ddcbe02a63da10ec814dc2654a04f220dc))

## [1.4.1](https://github.com/runpod-workers/flash/compare/v1.4.0...v1.4.1) (2026-04-09)


### Bug Fixes

* **ci:** add manual workflow to bump runtime dependencies ([#84](https://github.com/runpod-workers/flash/issues/84)) ([a5dc87a](https://github.com/runpod-workers/flash/commit/a5dc87a2f165364d229b2ae82e248b6a96981f7e))
* **deps:** bump runpod-flash 1.8.0 -&gt; 1.11.3, runpod 1.8.1 -&gt; 1.9.0 ([#86](https://github.com/runpod-workers/flash/issues/86)) ([f3ce708](https://github.com/runpod-workers/flash/commit/f3ce708ebb4674e65ad35c99be0f5763f71109a5))

## [1.4.0](https://github.com/runpod-workers/flash/compare/v1.3.0...v1.4.0) (2026-03-23)


### Features

* **http:** add Runpod Flash User-Agent to cross-endpoint requests ([#81](https://github.com/runpod-workers/flash/issues/81)) ([23782f8](https://github.com/runpod-workers/flash/commit/23782f81c1ab74bebab939def544cff239ff80e8))

## [1.3.0](https://github.com/runpod-workers/flash/compare/v1.2.0...v1.3.0) (2026-03-10)


### Features

* **handler:** on-the-fly package install for deployed mode ([#77](https://github.com/runpod-workers/flash/issues/77)) ([bc96b33](https://github.com/runpod-workers/flash/commit/bc96b3366c94847b3c7128c2d8f3185194fa09a0))

## [1.2.0](https://github.com/runpod-workers/flash/compare/v1.1.1...v1.2.0) (2026-03-10)


### Features

* Python version matrix for Docker images + error-masking fix ([#76](https://github.com/runpod-workers/flash/issues/76)) ([a9845c6](https://github.com/runpod-workers/flash/commit/a9845c6e8db75419c26e6f58a17737d7bb0fe25c))


### Bug Fixes

* **ci:** remove partial semver docker tags ([#73](https://github.com/runpod-workers/flash/issues/73)) ([4499808](https://github.com/runpod-workers/flash/commit/44998087a608a64b0e64020efeb5bf2320d1561f))

## [1.1.1](https://github.com/runpod-workers/flash/compare/v1.1.0...v1.1.1) (2026-02-26)


### Bug Fixes

* add runtime version banner, log after unpack for accuracy ([#71](https://github.com/runpod-workers/flash/issues/71)) ([74ea9ba](https://github.com/runpod-workers/flash/commit/74ea9ba7d0f2e4e2d97ced1a34d1c0b53cfbbcbc))
* **ci:** eliminate redundant CI runs and migrate release-please ([#70](https://github.com/runpod-workers/flash/issues/70)) ([002b787](https://github.com/runpod-workers/flash/commit/002b78790787ca56ff3fe127f21f714dbc43b7b1))

## [1.1.0](https://github.com/runpod-workers/flash/compare/v1.0.1...v1.1.0) (2026-02-25)


### Features

* fully deployed environment with generated handlers ([#68](https://github.com/runpod-workers/flash/issues/68)) ([59a7fcc](https://github.com/runpod-workers/flash/commit/59a7fcc7bb6ae7b31364ad1a1418d4c85cf8a32a))

## [1.0.1](https://github.com/runpod-workers/flash/compare/v1.0.0...v1.0.1) (2026-02-10)


### Bug Fixes

* move flash imports after maybe_unpack to fix torch import errors ([#63](https://github.com/runpod-workers/flash/issues/63)) ([f1bd8a3](https://github.com/runpod-workers/flash/commit/f1bd8a351b64d5e371119b7f8775a7533146ba9e))

## [1.0.0](https://github.com/runpod-workers/worker-tetra/compare/v0.7.5...v1.0.0) (2026-02-04)


### ⚠ BREAKING CHANGES

* rename tetra to flash ([#59](https://github.com/runpod-workers/worker-tetra/issues/59))

### Bug Fixes

* enable proper semantic versioning for breaking changes ([#61](https://github.com/runpod-workers/worker-tetra/issues/61)) ([7c4da51](https://github.com/runpod-workers/worker-tetra/commit/7c4da510c2797f11e610419cb61a6d532a5f1473))


### Code Refactoring

* rename tetra to flash ([#59](https://github.com/runpod-workers/worker-tetra/issues/59)) ([0580129](https://github.com/runpod-workers/worker-tetra/commit/058012909953cc2187a285bca8cfaadb75637160))

## [0.7.5](https://github.com/runpod-workers/flash/compare/v0.7.4...v0.7.5) (2026-02-03)


### Features

* add code intelligence with dependency indexing support ([#54](https://github.com/runpod-workers/flash/issues/54)) ([528ff8a](https://github.com/runpod-workers/flash/commit/528ff8a96d6100c282ebf0646a6f2e5f9b057160))
* add mothership mode for Flash deployment hosting ([#55](https://github.com/runpod-workers/flash/issues/55)) ([e82dadf](https://github.com/runpod-workers/flash/commit/e82dadf98276dcc333b75b3dd64a74e69024025c))


### Bug Fixes

* AE-1968: archive.tar.gz -&gt; artifact.tar.gz ([#57](https://github.com/runpod-workers/flash/issues/57)) ([1c3d0d9](https://github.com/runpod-workers/flash/commit/1c3d0d950f0b61ed6f19aa47232539104a0c6dcc))

## [0.7.4](https://github.com/runpod-workers/flash/compare/v0.7.3...v0.7.4) (2026-01-27)


### Features

* state manager manifest integration with TTL-based reconciliation ([#52](https://github.com/runpod-workers/flash/issues/52)) ([3683d6d](https://github.com/runpod-workers/flash/commit/3683d6dd5a3092a7c92e0226e2105ea45f2a2ab7))

## [0.7.3](https://github.com/runpod-workers/flash/compare/v0.7.2...v0.7.3) (2026-01-16)


### Features

* dual-mode runtime for Flash Deployed Apps and Live Serverless ([#50](https://github.com/runpod-workers/flash/issues/50)) ([fd568c2](https://github.com/runpod-workers/flash/commit/fd568c2c996d10551267e78053bb7b5e1d1a3f65))
* **load-balancer:** implement Live Load Balancer runtime Docker infrastructure ([#45](https://github.com/runpod-workers/flash/issues/45)) ([7cfe1b7](https://github.com/runpod-workers/flash/commit/7cfe1b713c12a1cfb259976d971fe2900109a104))
* unpack app tarballs from shadow volumes ([#49](https://github.com/runpod-workers/flash/issues/49)) ([55d9cec](https://github.com/runpod-workers/flash/commit/55d9cec2751ca6718c883ed5d85d1cffa42f2b35))


### Bug Fixes

* **ci:** resolve disk space issues and optimize Docker image sizes ([#46](https://github.com/runpod-workers/flash/issues/46)) ([7261ccb](https://github.com/runpod-workers/flash/commit/7261ccb5d0d20be83b47d67115959391f46383c4))

## [0.7.2](https://github.com/runpod-workers/flash/compare/v0.7.1...v0.7.2) (2025-12-03)


### Features

* pre-install git in Docker images ([#43](https://github.com/runpod-workers/flash/issues/43)) ([99ac555](https://github.com/runpod-workers/flash/commit/99ac55572e77d0b37cd7c01f536ac50eb8d604d9))

## [0.7.1](https://github.com/runpod-workers/flash/compare/v0.7.0...v0.7.1) (2025-11-14)


### Features

* configure release-please to include refactor commits ([#37](https://github.com/runpod-workers/flash/issues/37)) ([b8c59a0](https://github.com/runpod-workers/flash/commit/b8c59a0eef5f876a9cbbf524f48f2ce984b2b013))
* **executor:** add async function and method execution support ([#42](https://github.com/runpod-workers/flash/issues/42)) ([6b19ce6](https://github.com/runpod-workers/flash/commit/6b19ce678f091979b387657ec657959768861d4c))

## [0.7.0](https://github.com/runpod-workers/flash/compare/v0.6.0...v0.7.0) (2025-10-10)


### Features

* Endpoint Persistence using Network Volume (phase 1) ([#25](https://github.com/runpod-workers/flash/issues/25)) ([f59bec2](https://github.com/runpod-workers/flash/commit/f59bec228a93f075a4009bf0b17a3002d496df6e))
* Endpoint Persistence using Network Volume (phase 2) ([#31](https://github.com/runpod-workers/flash/issues/31)) ([657e89a](https://github.com/runpod-workers/flash/commit/657e89a91c9e36432d8720d8464179996b4f1e60))

## [0.6.0](https://github.com/runpod-workers/flash/compare/v0.5.0...v0.6.0) (2025-09-25)


### Features

* AE-1146 upgrade PyTorch base image to 2.8.0 with CUDA 12.8. ([#28](https://github.com/runpod-workers/flash/issues/28)) ([32b2561](https://github.com/runpod-workers/flash/commit/32b256182eccafa526dd8a45d1d3a8b2668dc08b))
* AE-962 streaming logs from remote to local ([#24](https://github.com/runpod-workers/flash/issues/24)) ([b1c9a47](https://github.com/runpod-workers/flash/commit/b1c9a4743ebf687559ca6542137913c4926f8ce9))


### Bug Fixes

* access built-in system Python instead of using venv for runtime ([#30](https://github.com/runpod-workers/flash/issues/30)) ([d11a7fb](https://github.com/runpod-workers/flash/commit/d11a7fba53d8336dd229b34954ca5cee9ec0ce9b))

## [0.5.0](https://github.com/runpod-workers/flash/compare/v0.4.1...v0.5.0) (2025-08-27)


### Features

* Add download acceleration for dependencies & hugging face ([#22](https://github.com/runpod-workers/flash/issues/22)) ([f17e013](https://github.com/runpod-workers/flash/commit/f17e013263605758f17360abe684fa3de8c2f89e))

## [0.4.1](https://github.com/runpod-workers/flash/compare/v0.4.0...v0.4.1) (2025-08-06)


### Bug Fixes

* CI-built docker images were broken ([317dc4e](https://github.com/runpod-workers/flash/commit/317dc4ec505f6e6cd59f61974342471a20b46467))
* last cleanup pr tag from docker did not work ([#19](https://github.com/runpod-workers/flash/issues/19)) ([d317991](https://github.com/runpod-workers/flash/commit/d3179910dd9febba149afaae3362011b859ee206))
* PR builds and tests input json files only ([#20](https://github.com/runpod-workers/flash/issues/20)) ([d6b61d7](https://github.com/runpod-workers/flash/commit/d6b61d7a0c5bd4da546f37757dec4166679fa631))
* production Docker builds and GPU/CPU tag consistency ([#17](https://github.com/runpod-workers/flash/issues/17)) ([9d65fde](https://github.com/runpod-workers/flash/commit/9d65fdeb1d4e373cea009cfe09d7d69d60407497))

## [0.4.0](https://github.com/runpod-workers/flash/compare/v0.3.1...v0.4.0) (2025-08-05)


### Features

* Workspace environment persisted in the network volume  ([#10](https://github.com/runpod-workers/flash/issues/10)) ([6675ec1](https://github.com/runpod-workers/flash/commit/6675ec1c52cc453be450684ce49ba4bea0d8ea2b))

## [0.3.1](https://github.com/runpod-workers/flash/compare/v0.3.0...v0.3.1) (2025-07-23)


### Bug Fixes

* broken ci ([#13](https://github.com/runpod-workers/flash/issues/13)) ([b25d822](https://github.com/runpod-workers/flash/commit/b25d8220ef0389dea6a83fd9a4450be459e79244))

## [0.3.0](https://github.com/runpod-workers/flash/compare/v0.2.0...v0.3.0) (2025-07-23)


### Features

* AE-835 Add class based execution [Runtime] ([#8](https://github.com/runpod-workers/flash/issues/8)) ([6d6505e](https://github.com/runpod-workers/flash/commit/6d6505ebdd749dff45dd52cb18b93da9330fe5ab))
* CI/CD pipeline workflows with testing, linting, valiation and docker builds ([#9](https://github.com/runpod-workers/flash/issues/9)) ([9d3d696](https://github.com/runpod-workers/flash/commit/9d3d69698238718ab64675b335630caf3c186526))


### Bug Fixes

* update Dockerfile to reference only existing files ([#12](https://github.com/runpod-workers/flash/issues/12)) ([93df475](https://github.com/runpod-workers/flash/commit/93df4756bea1c60adae9063cd2426ea230f3b7d5))

## [0.2.0](https://github.com/runpod-workers/flash/compare/v0.1.1...v0.2.0) (2025-06-26)


### Features

* AE-518 CPU Live Serverless ([#1](https://github.com/runpod-workers/flash/issues/1)) ([ddae70b](https://github.com/runpod-workers/flash/commit/ddae70b52e3ba261d2986e6485df6ec6307db368))


### Bug Fixes

* forgot these ([4048e97](https://github.com/runpod-workers/flash/commit/4048e977fffe46363cdd9baafaea18188b5d9e6f))
* release-please ([fb10504](https://github.com/runpod-workers/flash/commit/fb10504670459b272e12f49f8f77df23f3c0e8fe))

## [0.2.0](https://github.com/runpod-workers/flash/compare/v0.1.0...v0.2.0) (2025-06-26)


### Features

* AE-518 CPU Live Serverless ([#1](https://github.com/runpod-workers/flash/issues/1)) ([ddae70b](https://github.com/runpod-workers/flash/commit/ddae70b52e3ba261d2986e6485df6ec6307db368))


### Bug Fixes

* forgot these ([4048e97](https://github.com/runpod-workers/flash/commit/4048e977fffe46363cdd9baafaea18188b5d9e6f))

## 0.1.0 (2025-06-23)


### Bug Fixes

* forgot these ([4048e97](https://github.com/runpod-workers/flash/commit/4048e977fffe46363cdd9baafaea18188b5d9e6f))
