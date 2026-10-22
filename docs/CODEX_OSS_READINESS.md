# Codex for Open Source — application readiness (working draft)

**As of:** 2026-10-22 (Asia/Tokyo)  
**Project:** ART-NEWS / 幕间休息 (Intermission)  
**Repository:** https://github.com/k1ryulong6-source/ART-NEWS  
**Official form:** https://openai.com/zh-Hans-CN/form/codex-for-oss/
**Owner decision:** Prepare this public ART-NEWS project and the future fully open-source `linyining0604-pixel/taizidang` research project as **two distinct applications** by the **same real individual**, not by different people/accounts for multiple benefits.

> Working document only. Nothing in this file means OpenAI has approved an application. Do not fabricate stars, downloads, users, collaborators, releases or tests. This draft does **not** grant permission to change repository visibility, incur API costs, modify production workflows, or publish third-party content.

## Verified evidence and limits

- Repository is **public** and non-archived. Owner has write/maintain access.
- Public GitHub page showed **3,020 commits, 0 stars and 0 forks** on 2026-10-22. Commit count shows development activity, **not** adoption, independent contributions, or successful review.
- The README documents ingestion from **26 sources**, scheduled automation, provenance-aware metadata, static and Python server builds, local SQLite storage, and tests. Numbers in historical README sections must not be passed off as live metrics.
- Live site: https://mujianrest.work/ . A live public website does not establish active monthly users or OSS reuse.
- **Missing:** evidence of external adoption, downloads, independent contributors, regular maintenance reports and documented third-party reuse.
- **Licensing gap:** no root `LICENSE`, `LICENSE.md`, `LICENSE.txt` or `COPYING` was found. Public source visibility alone is not an open-source license. Do not add a license until original-code ownership and third-party inclusions have been checked.
- Research the terms for archived full text, translated articles, editorial summaries, images, datasets, fonts, JS/Python dependencies and other redistributed assets **separately**. Do not automatically place sourced articles or images under an original-code license.

## Proposed application copy (English, each field <500 characters)

**Maintainer role:** Primary maintainer — only if the applicant confirms this matches their actual responsibilities.

**Why does this repository qualify?** (445 characters)

ART-NEWS (Intermission) is an actively maintained public, self-hostable cultural information system with automated source ingestion, provenance-aware records, regression tests and multilingual reading workflows. It documents 26 sources and supports reproducible static and local-server deployment. I am its primary maintainer. External adoption is still early (0 stars, 0 forks); the aim is to make these workflows reusable by other maintainers.

**How will you use API credits?** (382 characters)

Use Codex API credits for core OSS maintenance only: review PRs for source adapters, generate and check parser regression tests, audit data-provenance checks, triage CI failures, improve release workflows and draft release notes. Changes will remain subject to maintainer review. Credits would not fund routine article translation, paywalled scraping, or unrelated private projects.

**Anything else we should know?** (360 characters)

This is an early-stage public project with substantial development activity but no demonstrated broad adoption yet. Repository contents include source-linked news metadata and some externally sourced material; licensing of original code must be distinguished from third-party text, images and data. We will not claim user/download numbers we have not measured.

**Other required fields, to be filled privately in the official form:** applicant's name, ChatGPT account email, GitHub username, repository URL, and the **actual** OpenAI organization ID from https://platform.openai.com/settings/organization/general . Do not commit personal contact details or organization IDs to this repository. The official form also provides optional selections for Codex Security and API credits.

## Before submitting — evidence and OSS readiness

- [ ] Confirm applicant's primary/core maintainer role and public GitHub profile.
- [ ] Confirm effective software licensing: inventory original code vs. third-party text, images, translations, fonts, data and licenses, then add an appropriate license **only for content we can license**. Do not default-license source journalism.
- [ ] Add `CONTRIBUTING.md` with build, tests, source acceptance criteria and PR review rules.
- [ ] Add a public reproducible starter/deployment path (without personal secrets or private data) and explain source-availability limits.
- [ ] Document release/change history and maintainer responsibilities; verify current CI/Actions and record the latest passing runs.
- [ ] Gather independently measured adoption evidence: unique site audience if legally and transparently measured, legitimate clones/deployments, outside issues/PRs, citations, package downloads. If unavailable, state that explicitly.
- [ ] Review tracked files and git history for secrets, personal data and third-party copyrighted material before inviting external cloning.
- [ ] Obtain the correct OpenAI organization ID directly from the applicant's account; never invent it.
- [ ] Manually submit through the official form. No application has been submitted by this PR.

## Suitable Codex maintenance workflows

1. Propose parser/adaptor regression tests when a source changes, preserving its provenance and publication dates.
2. Review PRs against the source/translation metadata schemas and quality gates.
3. Triage CI failures and improve reproducible packaging/release documentation.
4. Generate *draft* release notes from verified diffs, with human review.

Routine news translation, bulk acquisition of full copyrighted articles, and work in unrelated private apps are **not** the maintenance-credit rationale.

## Two submissions / identity consistency

- This application concerns **ART-NEWS only**; the separate future application will concern **the complete 权脉 (taizidang) project** after the research release is ready, its repository is made public, and legal/privacy/evidence audits pass.
- Both GitHub accounts may be maintained by the same person. OpenAI may request evidence of control; always use one truthful applicant identity and the correct ChatGPT email, with both profiles disclosed as necessary.
- The Program Terms prohibit using multiple identities or accounts to obtain more than one benefit. Two projects do **not** entitle the maintainer to two ChatGPT Pro awards. Any award/credit scope is determined by OpenAI.
- ART-NEWS is already public and can be prepared sooner; the future private-research-to-public conversion must **not** delay this project's OSS readiness work or misstate the other project's eligibility.

## Decision checkpoint

**Status:** plausible early-stage candidate, **not yet a strong demonstrated ecosystem-adoption candidate**. Address licensing and reuse first. Application outcome is decided solely by OpenAI, under its rolling review process.
