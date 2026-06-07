# Building an AI GitHub Workflow Copilot

Most AI portfolio projects stop at a chat interface. I wanted to build something closer to how software teams actually work: issues, pull requests, CI failures, labels, priorities, and review checklists.

AI Dev Workflow Copilot is an event-driven triage system for GitHub workflows. It accepts an Issue or Pull Request URL, or a GitHub webhook payload, fetches repository context, and produces structured engineering output: category, priority, impacted modules, likely causes, action plan, test plan, acceptance criteria, and a maintainer-ready comment.

## Why This Project

Developer workflows contain repeated judgment work:

- Is this a bug, feature, documentation task, refactor, or security issue?
- How urgent is it?
- Which module is likely affected?
- What tests should be added before closing?
- What should a maintainer say to move the work forward?

These tasks are good fits for AI assistance because they combine natural-language context with engineering conventions.

## System Design

The backend is a FastAPI service. It exposes:

- `POST /api/analyze` for GitHub URLs.
- `POST /api/webhooks/github` for real GitHub webhook events.
- `POST /api/webhooks/simulate` for demos without webhook setup.
- `POST /api/analyze/ci-log` for pasted CI or test failure logs.
- `GET /api/tasks` and `GET /api/tasks/{id}` for the dashboard.

The GitHub client fetches Issue or PR data, README context, changed files, and check-run summaries when available. The analyzer uses DeepSeek if configured, and otherwise falls back to deterministic keyword rules. This fallback is important because a portfolio demo should still work without paid credentials. The repository also includes a small labeled evaluation set for category and priority accuracy, so the project can discuss AI quality rather than only AI output.

## Security Decisions

The project treats automation carefully. Reading context is safe for public repositories. Writing comments or labels requires `GITHUB_TOKEN`, and those actions are optional. Webhook signatures are verified when a secret is configured. API keys stay in backend environment variables and are never exposed to the frontend.

## What I Learned

The main engineering challenge is not just calling an LLM. The useful part is shaping the workflow around the model:

- Pull the right context.
- Ask for structured output.
- Store workflow state.
- Keep a deterministic fallback.
- Gate write actions behind explicit permissions.
- Make the result easy for maintainers to scan.

## Future Improvements

The next production step would be a GitHub App instead of personal tokens, PostgreSQL instead of SQLite, Redis/RQ for queueing, and an evaluation set of labeled issues to measure category and priority accuracy.

This project is a good internship portfolio piece because it connects AI engineering with everyday software engineering workflows.
