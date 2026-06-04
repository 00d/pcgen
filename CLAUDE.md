# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A more exhaustive working-notes file lives at `AGENTS.md` in the repo root — treat it as the canonical reference for commands, layout, source sets, CI, and release flow. The notes below are the high-signal subset most relevant when writing code here.

## Project at a glance

PCGen — a JavaFX desktop application for creating and managing RPG characters. Built with Gradle (use the wrapper), targets **Java 25 (Temurin)**. Main entry point: `code/src/java/pcgen/system/Main.java`.

The project is composed of three Gradle builds: the main `pcgen` module (this repo), plus sibling builds `PCGen-base/` and `PCGen-Formula/` whose jars are placed on the JPMS module path.

## Common commands

Always use `./gradlew` (the wrapper). Java 25 must be on `JAVA_HOME`.

| Task | Command |
| --- | --- |
| List all tasks | `./gradlew tasks` |
| Run the app (GUI) | `./gradlew run` |
| Unit tests (`code/src/utest`) | `./gradlew test` |
| Integration tests (`code/src/itest`) | `./gradlew itest` |
| Slow tests (`code/src/test`) | `./gradlew slowtest` |
| Data tests | `./gradlew datatest` |
| Single test class | `./gradlew test --tests fully.qualified.ClassName` |
| Full pre-PR check (mirrors CI) | `./gradlew build` then `./gradlew itest datatest slowtest` |
| Coverage report | `./gradlew testCoverage` (HTML in `build/reports/jacoco/testCoverage/html`) |
| Quality (Checkstyle/PMD/SpotBugs) | `./gradlew allReports` |
| Native bundle | `./gradlew fullJpackage` (NOT `jpackageImage` — it skips copying `data/`, `plugins/`, `preview/`, `outputsheets/`) |
| Clean | `./gradlew clean` (also runs cleanPlugins/cleanOutput/cleanJdks/cleanMods/cleanMasterSheets) |

Pass CLI args to the app via `./gradlew run --args="..."`. Flags are parsed in `pcgen/system/CommandLineArguments.java`; tests for them live next to it in `code/src/utest/pcgen/system/CommandLineArgumentsTest.java`.

## Source set layout (non-standard — matters when adding tests)

- `code/src/java` — production code (`pcgen.*` packages)
- `code/src/utest` — fast unit tests → `./gradlew test`
- `code/src/itest` — integration tests → `./gradlew itest`
- `code/src/test` — slow tests → `./gradlew slowtest`
- `code/src/testcommon`, `code/src/testResources` — shared fixtures

Placing a test in the wrong directory means the corresponding Gradle task won't pick it up.

Build logic is split across `code/gradle/*.gradle` (plugins, distribution, reporting, release, autobuild). Look there before editing the root `build.gradle`.

## Architecture notes worth knowing up front

- **Top-level package layout under `pcgen`:** `cdom` (Common Data Object Model — the core data structures), `core` (rules engine), `rules`, `persistence` (LST file parsing/loading), `io` (export — uses FreeMarker templates in `outputsheets/`), `output`, `gui2`/`gui3` (Swing + JavaFX UI), `facade` (UI ↔ core boundary), `system` (bootstrap, CLI, lifecycle), `pluginmgr`, `format`, `util`.
- **Runtime data lives outside `code/`.** `data/`, `system/`, `outputsheets/`, `preview/`, `vendordata/`, `homebrewdata/`, `plugins/` are all read at runtime; `Main.validateEnvironment()` will fail if the layout is broken. Distribution zips assemble from these via `code/gradle/distribution.gradle`.
- **Plugins are built as separate jars** by tasks in `code/gradle/plugins.gradle`. The main jar depends on `jarAllPlugins`.
- **JPMS split-package hazard.** The `pcgen` module is built with `--patch-module` merging most deps in, while `PCGen-base` and `PCGen-Formula` stay separate modules. **Do not add any class in this repo whose package already exists in those jars** — Java forbids split packages across modules. The previously conflicting `pcgen.base.util` and `pcgen.base.format` packages were relocated to `pcgen.util` and `pcgen.format`; preserve that.
- **Java/JavaFX coupling.** `project.ext.javaVersion` (25) and the JavaFX module list flow through `run`, `test`, `JavaCompile`, distribution, and jpackage tasks. Changing one usually requires touching all of them and CI.

## Project-specific conventions

- **Never call `System.exit` directly** — use `pcgen.util.GracefulExit.exit`. Checkstyle enforces this via a RegexpMultiline rule; tests hook the exit function.
- Checkstyle, PMD, and SpotBugs (with findsecbugs) configs live under `code/standards/`. Line length cap is 201; newline at EOF required.
- Some build repos use `allowInsecureProtocol = true` (HTTP). Do not change without coordinating with maintainers.
- Headless test setup (TestFX/Monocle, JavaFX module path, asserts on, 1024m heap, `maxParallelForks=1`) is applied to Test tasks — don't replicate it ad hoc.
- **Plugin loading in tests goes through `@ExtendWith(PCGenTestEnvironment.class)`** (`code/src/testcommon/pcgen/test/PCGenTestEnvironment.java`) — a JUnit 5 extension that calls `Main.createLoadPluginTask().run()` exactly once per JVM. Don't hand-roll plugin loading in new tests; `AbstractCharacterTestCase` / `AbstractJunit5CharacterTestCase` already inherit it. It is intentionally **opt-in**: plugin loading populates the global `PluginFunctionLibrary`, which every newly constructed `VariableContext` snapshots at construction time, so tests that depend on an empty function library (e.g. `SetSolverManagerTest`) must NOT extend it. The extension does not load game data — tests that need real data (e.g. `DataTest`, `DataLoadTest`) still drive `GameModeFileLoader` / `CampaignFileLoader` themselves.

## Running quick scenarios

- Launch GUI: `./gradlew run`
- Name generator: `./gradlew run --args="--name-generator"`
- Batch export (see `code/src/test/pcgen/inttest/PcgenFtlTestCase.java` for the canonical example):
  ```
  ./gradlew run --args="--character path/to/char.pcg --exportsheet outputsheets/.../sheet.ftl --outputfile /tmp/out.xml --configfilename config.ini.junit"
  ```
