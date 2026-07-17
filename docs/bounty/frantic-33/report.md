# WeCom Agent Sourcey documentation report

## Delivery summary

- Published a Sourcey 3.6.5 documentation site for `tzwkb/wecom-agent`, an MIT-licensed Python library pinned at source commit `5fb2ca070d9a42f80d21b19e9dafc9e6fdcad5e9`.
- Added ten navigable pages covering setup, local reading, normal documents, standard sheets, smart sheets, MCP tools, security, API reference, and troubleshooting.
- Documented 38 public Python APIs from repository source, above the required 20-entry threshold.
- Kept generated HTML outside the authored docs tree and added project-level ignores for Sourcey output and local run receipts.
- Published the Sourcey 3.6.5 site at `wecom-agent.readthedocs.io` from the connected repository's `main` branch using the committed `.readthedocs.yaml`, and linked it from both project READMEs.
- Verified Read the Docs build `#33627849` at deployment commit `b2850245f5dd9599cd7d53eece069816a25e886a`.
- Sealed the governed Sourcey run as `runx:receipt:sha256:9c6f92e140c4f6546e5133bb6bfa7bfbd70c9ec087050ee539dced298af9fba9` using `runx-cli 0.7.1`.
- Rebuilt independently after the governed run: 14 unit tests passed, all ten pages were non-empty, all 38 API entries rendered, and no local links were broken.
- Rechecked the live site as a stranger: ten pages, six core assets, and all twelve unique relative link targets returned HTTP 200; the live API reference contains 45 rendered section headings.
- Validated all four Sourcey card icons against Heroicons v2 outline and generated `llms.txt`, `llms-full.txt`, search index, sitemap, and Open Graph images.

## Maintainer-facing gaps

- **Public API documentation remains mostly external to the code.** Of 37 public functions sampled in the online and local document modules, only one has a docstring and none has a return annotation. The new reference is useful now, but adding source docstrings and return types would make future API pages easier to regenerate and harder to drift.
- **Installation is not packaged reproducibly.** The repository has no `pyproject.toml`, requirements file, or lockfile; `setup.sh` installs a broad global dependency set. A package manifest with optional dependency groups would separate core wrappers from macOS capture, document parsing, and transcription dependencies.
- **Online capability support is version-sensitive.** The current boundary is tied to `wecom-cli 0.1.9`, which lacks `get_doc_content`, `sheet_get_data`, and `smartsheet_get_records`. Recording CLI schema snapshots in CI would make additions and removals visible before documentation claims become stale.
- **Live enterprise permissions are not covered by repeatable integration fixtures.** Unit tests correctly inject runners, but contact, message, schedule, meeting, document, and sheet permission behavior can vary by enterprise. Sanitized contract fixtures would let maintainers distinguish unsupported commands from transient authentication failures.
- **Platform compatibility is described but not continuously tested.** macOS and Windows share the crypto core but use different key discovery and orchestration layers. A small compatibility matrix tied to WeCom desktop versions would help users know which paths were recently exercised.
- **Python changes still lack a pull-request quality gate.** Read the Docs now rebuilds the Sourcey site from `main`, but the repository has no CI job that runs the 14 unit tests before merge. Adding that check would protect the wrappers and examples before the documentation deployment begins.

## Why this is a credible home

The live site has a dedicated `wecom-agent.readthedocs.io` project on an established documentation platform. It is connected directly to `tzwkb/wecom-agent`, rebuilds from the repository's `main` branch through the committed Read the Docs configuration, and is linked from the English and Chinese READMEs. It is not a personal-handle GitHub Pages host, fork preview, detached demo repository, or unrelated domain. The source, deployment configuration, adoption links, evidence, and report are all reviewable in the maintained target project.
