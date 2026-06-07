# Portfolio Guide

Use this page when presenting the project in a resume, interview, internship application, or freelance proposal.

## One-Line Pitch

AI Dev Workflow Copilot is an event-driven GitHub automation system that turns issues, pull requests, webhook events, and CI failure logs into structured engineering triage decisions.

## Why It Is Stronger Than a Chatbot Demo

- It is triggered by real software engineering events: Issue, PR, webhook, and CI failure.
- It fetches context from GitHub instead of asking users to paste everything manually.
- It returns structured output that a maintainer can act on: labels, priority, impact area, fix plan, test plan, acceptance criteria, and review checklist.
- It has deterministic fallback rules, so the demo still works without an LLM key.
- It has tests, CI, Docker Compose, deployment configuration, and a small evaluation dataset.

## Demo Checklist

1. Open the online dashboard.
2. Show backend status and explain fallback mode.
3. Paste a public GitHub Issue or PR URL and run analysis.
4. Run the webhook simulator to show event-driven workflow behavior.
5. Paste the sample CI failure log and show the CI-specific action plan.
6. Open the GitHub repo and show tests, GitHub Actions, Docker Compose, and docs.
7. Mention that automatic GitHub labels/comments are disabled unless a token is configured.

## Resume Bullets

- Built an AI-powered GitHub workflow automation system that analyzes issues, pull requests, webhook events, and CI logs into category, priority, labels, impact modules, action plans, test plans, and maintainer-ready comments.
- Integrated FastAPI with GitHub REST APIs, webhook signature verification, SQLite task storage, and optional GitHub label/comment automation.
- Implemented a Next.js dashboard with task polling, webhook simulation, CI failure analysis, and graceful fallback demo mode.
- Added deterministic triage rules, pytest coverage, frontend lint/typecheck/build checks, Docker Compose, GitHub Actions CI, and an evaluation script with accuracy thresholds.

## Interview Talking Points

- Webhook safety: verify `X-Hub-Signature-256` before trusting GitHub payloads.
- Reliability: keep a deterministic fallback analyzer so demos and CI are not blocked by paid LLM APIs.
- Product thinking: output is not just a model response; it is a maintainer workflow with labels, plans, criteria, and review checklist.
- Evaluation: use labeled triage cases to track category and priority accuracy over time.
- Scaling path: move SQLite to PostgreSQL, background tasks to Redis/RQ or Celery, and personal tokens to a GitHub App installation flow.

## What To Improve Next

- GitHub App OAuth and installation flow.
- PostgreSQL task store with per-user repository isolation.
- Redis-backed queue for high-volume webhook events.
- Automatic ingestion of GitHub Actions job logs.
- Larger evaluation set with human-labeled issues, PRs, and CI failures.
