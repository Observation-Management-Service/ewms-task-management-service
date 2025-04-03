# Changelog

<!--next-version-placeholder-->

## v1.0.0 (2025-04-03)

### Breaking

* Co-authored-by: github-actions <github-actions@github.com> ([`68dcf78`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/68dcf78f21406198006e2a16af757ab4e0122e91))

## v0.1.64 (2025-04-03)

### Other

* Update Production Scripts ([#38](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/38)) ([`3dc2cbc`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/3dc2cbc74b949394fe5701bcaa1570e91faf22d9))

## v0.1.63 (2025-04-02)

### Other

* Spilt/Duplicate Systemd Config for `ewms-prod` + `ewms-dev` ([#36](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/36)) ([`1180705`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/11807058a66b0a5c77069f151b7bb6daac370894))

## v0.1.62 (2025-03-28)

### Other

* Exclude Sites: "AMNH" and "NotreDame" (plus a new helper script) - 2 ([`b8d237c`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/b8d237cf7fb419ace7484440e68360ccbb4158c0))
* Exclude Sites: "AMNH" and "NotreDame" (plus a new helper script) ([`437a8bf`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/437a8bfb743d18632fd87c7d6d553e552d2a5a5e))

## v0.1.61 (2025-03-27)

### Other

* Update `pilot_config.image_source`: "auto" ([`a12eb1c`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/a12eb1c9fa64c1211a852381dbec37e6f7f40a71))

## v0.1.60 (2025-03-27)

### Other

* Add retries to `update_tms_image_symlink.sh` ([`4d60b97`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/4d60b97053403a0c998737aeedd6a972f6204639))
* Merge remote-tracking branch 'origin/main' ([`92284ec`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/92284ec42d0929af2eec58a8a8d86f8ee0bb24b0))
* Update `update_tms_image_symlink.sh` ([`d948fff`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d948fff7abc7ecccfaeee36dc8ba77b47e7bd9ab))

## v0.1.59 (2025-03-27)

### Other

* Use `pilot_config.image_source` ([#35](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/35)) ([`31a9490`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/31a9490282633342b7c05873a19959f4acbc7d99))

## v0.1.58 (2025-02-26)

### Other

* Exclude Sites Lacking Apptainer Support ([#34](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/34)) ([`347468b`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/347468b630fae42d6484d0f6ce870735c49ba6da))

## v0.1.57 (2025-02-26)

### Other

* Add systemd Helper Script ([#33](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/33)) ([`ea9c92c`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ea9c92c12ddc183a60f2d99874b40f91be5a4098))

## v0.1.56 (2025-02-24)

### Other

* Move systemd logging to /scratch/ewms instead of journal ([`de37ab2`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/de37ab2a743d7240da88237c6425dc986c81f4a6))

## v0.1.55 (2025-02-21)

### Other

* Remove directives that dont work with user systemd; fix working dir path ([`ff36fae`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ff36fae6b8545982f2a50d5c58de7d6cd7675ee5))

## v0.1.54 (2025-02-20)

### Other

* `systemd` File: Remove Env Var Refs, Add Restarter ([#32](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/32)) ([`fb644ed`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/fb644ede9a7db35c3a68cf75556cf9080642b03d))

## v0.1.53 (2025-02-18)

### Other

* Add systemd File ([#31](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/31)) ([`46f3a89`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/46f3a897b961dc775349368db6de21783fac2eac))

## v0.1.52 (2024-11-11)

### Other

* <bot> update dependencies*.log files(s) ([`b11464b`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/b11464beee6fc58bcfb12abb09408ca0dd0697c3))
* Use New "Next to Start" Schema ([#26](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/26)) ([`13ddb95`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/13ddb956c14be0c0805a8aacbec529822505d098))

## v0.1.51 (2024-10-31)

### Other

* Use User-Provided Condor Requirements ([#25](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/25)) ([`1563139`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/15631390325bf80715d3f769dd4c0bef27a164fd))

## v0.1.50 (2024-10-29)

### Other

* Followups from Skymap Scanner Test Runs ([#23](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/23)) ([`62e7500`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/62e75007e7d1656ea457ab977ef3c83664c71e80))

## v0.1.49 (2024-08-26)

### Other

* <bot> update README.md ([`c68e1ed`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/c68e1edc005c573f880f175833364488e8ee0b62))
* Update README Followups ([`d8dcdb7`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d8dcdb768c7216b8d82b0b34fb1def60c9bcb1da))

## v0.1.48 (2024-08-26)

### Other

* Update README ([#21](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/21)) ([`908647f`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/908647fa253824887df262948bba64f93e5945d2))

## v0.1.47 (2024-08-22)

### Other

* <bot> update dependencies*.log files(s) ([`9000349`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/9000349d9b829a994cec23f5f6f429dbedec98f2))
* Update Log File Detection - 2 ([`0404ced`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/0404ced91123e2c1b56088b94c5a854a26b86726))
* Update Log File Detection ([`4dd7498`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/4dd7498698c04a0a6d7045696b57b31b4cd63312))

## v0.1.46 (2024-08-20)

### Other

* Fix Chirp Parsing - 2 ([`51ff86d`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/51ff86db0e8aafdabb50b9d329a0f73f5cc962be))
* Fix Chirp Parsing ([`ef06b37`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ef06b377c60225eeb4fb863d901795c8bb0d9741))
* Log Taskforce ID ([`c79f74d`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/c79f74d4ccc2a09e4b3dc9db53952d6ab83b28e6))

## v0.1.45 (2024-08-20)

### Other

* <bot> update dependencies*.log files(s) ([`cb8932a`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/cb8932af24690f6de53969b1ecac674a955b3c1e))
* Demote Some Loggers to "debug" ([`921a8d3`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/921a8d3055e1ce5af374a0265a37b0bbbdd52d37))

## v0.1.44 (2024-08-09)

### Other

* Handle Failed Condor Submit - 2 ([`5d46997`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/5d46997a4929ded37f5682e8d3cf6b24f077f07f))
* Make the Release ([`f58e593`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/f58e59384ae1c67c93f2285aa0637f44e4a83847))
* Handle Failed Condor Submit ([`78c44b7`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/78c44b738358dbc2dc193d84675a375326ab8fc3))

## v0.1.43 (2024-08-09)

### Other

* Disallow New-Lines in Task Env Vars ([`98d4bbd`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/98d4bbd22d5740386713569dc7ad1b9787c9c636))

## v0.1.42 (2024-08-09)

### Other

* Remove `has_avx2` Requirement ([`5bfd0b8`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/5bfd0b859d847c8de4fa24f14c134e8704b40c8a))

## v0.1.41 (2024-08-09)

### Other

* Add `OSG_OS_VERSION =?= 8` to Starter Requirements - 3 ([`25df53f`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/25df53f6e51121f1bdb36534e5d9b76273452f0a))

## v0.1.40 (2024-08-08)

### Other

* <bot> update dependencies*.log files(s) ([`35bdb2d`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/35bdb2d66514a516a913499ad4fe572e789b3a2b))
* Add `OSG_OS_VERSION =?= 8` to Starter Requirements - 2 ([`79173fb`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/79173fbc1da0d543ac0e51cc83b49bd4d4b438ce))
* Add `OSG_OS_VERSION =?= 8` to Starter Requirements ([`d926320`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d9263206b3a55191ff131c24e7c27764b540b85c))

## v0.1.39 (2024-08-08)

### Other

* <bot> update dependencies*.log files(s) ([`83498ba`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/83498ba08a3b59ce0e043989f1a66d0840400a41))
* Add `TMS_ENV_VARS_AND_VALS_ADD_TO_PILOT`, Don't Override WMS Values ([`332a34b`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/332a34b373d2ed809548385efa16e7e3456e402a))

## v0.1.38 (2024-07-31)

### Other

* Prepend CVMFS Path to `pilot_image` - 2 ([`83474f3`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/83474f3411152c093ec7b32f5b8968c9161e9a08))

## v0.1.37 (2024-07-31)

### Other

* <bot> update dependencies*.log files(s) ([`d79e7bb`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d79e7bba3c22bdd8752808bf247469427a5f3c58))
* Prepend CVMFS Path to `pilot_image` ([`09fc9b8`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/09fc9b8f27f133a973a53c882d11c6e641af8ecb))

## v0.1.36 (2024-07-30)

### Other

* Allow Spaces in Env Var Values - 2 ([`a3f587f`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/a3f587f7be19b8f22418e509fda32190c740bdab))

## v0.1.35 (2024-07-30)

### Other

* Allow Spaces in Env Var Values ([`f569727`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/f569727c5e0313d2f6b1851dff0533182044633c))

## v0.1.34 (2024-07-30)

### Other

* Use `pilot_config` ([#20](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/20)) ([`72734d1`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/72734d12e51ff4b760f56ca045bccd3299f2a9d9))

## v0.1.33 (2024-07-30)

### Other

* Fix Chirp Parsing ([`86fad8a`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/86fad8aeccee6a51768da9ae23d92c98081f7847))

## v0.1.32 (2024-07-29)

### Other

* <bot> update dependencies*.log files(s) ([`1def75b`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/1def75b36baf6050f7b8ae65b4bab4262c175e12))
* Don't Log Unimportant Job Events ([`8ce7f73`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/8ce7f73bf7beff314d40d2ef255c6bd590796fa0))

## v0.1.31 (2024-06-28)

### Other

* <bot> update dependencies*.log files(s) ([`824b14a`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/824b14a5fdfafa83347cf06ca065717494fbd2f3))
* <bot> update setup.cfg ([`a6b8290`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/a6b8290bb86fc3b2f22e19d9ec6a7344771b0a24))
* Pin `htcondor==23.7.2` ([`52cc327`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/52cc3275782688949cb4625d01d151965d57d667))

## v0.1.30 (2024-06-28)

### Other

* Bump to `apptainer-version: 1.3.2` ([`509ec08`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/509ec08c774f10c7e1396a223b799a827ae09ccd))
* <bot> update dependencies*.log files(s) ([`438dfcf`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/438dfcf00ff0ba5667dd311ccbe05790656b2faf))
* Update for WMS List-Based Env Var Values ([`0e2b8b1`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/0e2b8b103ad2d71058b98813117c812d3ce60922))

## v0.1.29 (2024-06-05)

### Other

* <bot> update dependencies*.log files(s) ([`ea38ae1`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ea38ae1dcedeea298a4f8e49fd6cfaff214df967))
* <bot> update README.md ([`affa699`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/affa69966ca600b43a725e5088588c7a6f5b49ce))
* Update README ([`ce4c459`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ce4c45900779a3d457048ac41be5971330f1fe37))

## v0.1.28 (2024-06-03)

### Other

* Update WMS Requests ([#19](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/19)) ([`aca4f27`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/aca4f2792a45bd29a69622704878f0ee39735e10))

## v0.1.27 (2024-05-01)

### Other

* Add `LOG_LEVEL_REST_TOOLS` ([`4a37647`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/4a3764798822321d115c6505ba7a47aa1acd83e9))

## v0.1.26 (2024-05-01)

### Other

* <bot> update dependencies*.log files(s) ([`20b0cfd`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/20b0cfd1a845a80cf9789fb9b1e976034218a233))
* Update CI ([`ae24e4b`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ae24e4b5baf0d963d9ea77e950d8c2b1ad89ad6d))

## v0.1.25 (2024-04-24)

### Other

* <bot> update dependencies*.log files(s) ([`5605d5e`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/5605d5ecf38d38fc812138624d07c6ac91c3163d))
* Update to Use WMS's `phase` ([`86f60b1`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/86f60b1966e347b736dacb33a18146b1a8e2455d))

## v0.1.24 (2024-03-15)

### Other

* Logging Fix - 2.1 ([`5c2c18d`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/5c2c18dc174882726d2f3aa05124bf2987ed8303))
* Logging Fix - 2 ([`e48538e`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/e48538e2d3e7cbbdb8c057cb834a3eb3b9d490e3))

## v0.1.23 (2024-03-15)

### Other

* Logging Fix ([`a330f2c`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/a330f2c9bcea081bd31c4a6d51d342b88a9fa579))

## v0.1.22 (2024-03-14)

### Other

* Remove `examples/` ([#18](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/18)) ([`2455c25`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/2455c259a721b46d8f79773da264a05e5b028e70))

## v0.1.21 (2024-03-14)

### Other

* Add `HAS_SINGULARITY` to Condor Requirements ([`0214f92`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/0214f92075c24daf7dd255e915b259ed49600951))

## v0.1.20 (2024-03-13)

### Other

* Speed Up Example Script ([`170093a`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/170093a4863f37b65562edcbad5387007e8e651c))

## v0.1.19 (2024-03-13)

### Other

* Watcher: Ignore Non-Files in JEL Dir ([`ec5c008`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/ec5c00804330707ac185bd72d676de3d2bad2ac5))

## v0.1.18 (2024-03-13)

### Other

* Update Deps for Example Script ([#17](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/17)) ([`f1aa812`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/f1aa81269d014cba63268590dc31057f1d7ee3e6))

## v0.1.17 (2024-03-13)

### Other

* Use HTCondor's `universe=container` - 2 ([`3084d8c`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/3084d8cbb67a6277d1e10aaf5133981607b545e4))

## v0.1.16 (2024-03-13)

### Other

* Use HTCondor's `universe=container` ([#16](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/16)) ([`f26c9b2`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/f26c9b28592a0b38b5b0c1c0d64b035e5408d06b))

## v0.1.15 (2024-03-12)

### Other

* Starter: Make Output Subdir - 3 ([`c20e8ab`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/c20e8ab72f3c194ff220ca3365510198f42457d1))

## v0.1.14 (2024-03-12)

### Other

* Starter: Make Output Subdir - 2 ([#15](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/15)) ([`e756be5`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/e756be5adb7c60df9318f7d4ae5bafd6fc18db8a))

## v0.1.13 (2024-03-12)

### Other

* Starter: Make Output Subdir ([#14](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/14)) ([`97042c1`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/97042c147d175124e3fe777c80058dc032047a29))

## v0.1.12 (2024-03-12)

### Other

* Add Example Script ([#13](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/13)) ([`b05c7e6`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/b05c7e69b420c901738aa3f293a68248e957c13c))

## v0.1.11 (2024-03-08)

### Other

* Starter: Auto Set `ewms-pilot` Env Vars ([#12](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/12)) ([`7abded0`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/7abded0399fa6ad692933f518cfb9aa07b9c28a9))

## v0.1.10 (2024-03-07)

### Other

* Fix Condor File Transfering ([#11](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/11)) ([`4e14d24`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/4e14d24aa49be1d3c32c4ba41790edefa5556afb))

## v0.1.9 (2024-03-06)

### Other

* Update Logging and `/taskforces/tms/status` ([#10](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/10)) ([`d242650`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d242650b0d5d64f439259b0e000a6cefd530f1f1))

## v0.1.8 (2024-03-06)

### Other

* Error Handling for EWMS Reports ([#9](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/9)) ([`db0e41f`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/db0e41f1134bfbdd8a438136bff166ea242541c4))

## v0.1.7 (2024-03-06)

### Other

* <bot> update dependencies*.log files(s) ([`e05b77d`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/e05b77d2ad4b910e2a2f1edc00f508c7f02e5e76))
* Condor args: escape embedded quotes ([`d753002`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d7530026c3eec0c0d5bffb7234905dbf704cbc5c))

## v0.1.6 (2024-03-06)

### Other

* Miscellaneous Updates (logging, modularization, etc) ([#8](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/8)) ([`951e69f`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/951e69fd5a245a58776ce99914676a533feea160))

## v0.1.5 (2024-03-05)

### Other

* Use Client Credentials for REST Auth ([#7](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/7)) ([`eaf30cd`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/eaf30cd4b0e11541da7456232837ac3b17c07577))

## v0.1.4 (2024-03-05)

### Other

* Auto-detect Collector and Schedd DNS ([#6](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/6)) ([`95b6f42`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/95b6f4241cc56fe453a85b12c0493230fcd4eda4))

## v0.1.3 (2024-03-05)

### Other

* Add more logging (esp. at start up) ([`93c9740`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/93c9740e7d47f28df43a75366b2be63ccd22cfe7))

## v0.1.2 (2024-03-04)

### Other

* Use Python Venv in `Dockerfile` for Apptainer ([#5](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/5)) ([`7404522`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/740452279df5254c2c99be1b76c82ee71fc67faf))

## v0.1.1 (2024-02-28)

### Other

* Updates for WMS REST Schema ([#4](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/4)) ([`b867605`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/b867605ee2b7155ca3486ce7e3fcdeca8e2f343f))

## v0.1.0 (2024-01-23)



## v0.0.2 (2023-12-18)

### Other

* Rm .github/workflows/publish.yml ([`dfa9984`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/dfa998476210715860ad9e027f2b3a182f2dad9e))
* Add `delete` trigger ([`d3a4a53`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/d3a4a5329e5fc93df4b3be0e865851d6efdb3bd3))

## v0.0.1 (2023-12-18)

### Other

* First PR ([#1](https://github.com/Observation-Management-Service/ewms-task-management-service/issues/1)) ([`75387f8`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/75387f84455a50aa0e522153f63b973a4add43ae))
* Initial commit ([`eba24ad`](https://github.com/Observation-Management-Service/ewms-task-management-service/commit/eba24ad862f264b091f778400335b13332499fde))
