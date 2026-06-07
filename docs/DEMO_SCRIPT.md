# Demo Script

Use this script for a 60-90 second portfolio video.

## Before Recording

1. Configure `DEEPSEEK_API_KEY` on the backend host.
2. Open the dashboard.
3. Keep a public GitHub issue URL ready.
4. Keep the Webhook Simulator payload visible for a no-auth demo path.

## Demo Flow

1. Open the dashboard and show backend status.
2. Paste a GitHub Issue URL and click Analyze.
3. Show the task moving through `received`, `fetching_context`, `analyzing`, and `completed`.
4. Show category, priority, confidence, labels, impact modules, action plan, and test plan.
5. Copy the maintainer comment and explain how it could be posted back to GitHub.
6. Run the Webhook Simulator payload.
7. Show recent task history.

## What To Say

This project turns GitHub events into structured engineering decisions. It is not a chatbot; it is an event-driven workflow: webhook or URL input, GitHub context retrieval, AI/heuristic analysis, task storage, and a dashboard for maintainers.

## Interview Talking Points

- Why webhook signature verification matters.
- How the fallback analyzer keeps demos deterministic.
- Why automatic comments and labels should be gated by permissions.
- How this would scale with a queue and PostgreSQL.
- How to evaluate triage accuracy with a labeled issue dataset.

