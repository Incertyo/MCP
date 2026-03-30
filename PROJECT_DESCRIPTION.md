# Cloud Optimizer MCP

Cloud Optimizer MCP is a full-stack cloud optimization demo built for presentations, prototypes, and student cloud-management showcases.

It combines a React frontend and FastAPI backend to demonstrate:

- cloud cost visibility
- optimization recommendations
- chatbot-assisted reasoning
- mocked and real AWS account onboarding
- observability and telemetry workflows

## Core idea

The app simulates an AI-assisted cloud optimization experience where a user can connect an AWS student account, view current resource posture, review recommendations, accept or reject optimization actions, and immediately see the effect across the dashboard.

## Highlights

- Modern glassmorphic UI with dark mode
- Dashboard with KPIs, line graph, pie chart, and service inventory
- Impact Studio for recommendation decisions and recurring demo replay
- Optimization Copilot chat with Gemini-ready backend integration
- Mock AWS mode for clean demos
- Real AWS mode for backend-only credential validation
- Observability panel with metrics and events feed
- FastAPI backend structured for DynamoDB and Datadog workflows
- Vercel deployment for both frontend and backend

## Tech stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, Pydantic
- Cloud/data: DynamoDB-ready repository layer
- Observability: Datadog-style telemetry hooks
- LLM: Gemini-ready backend integration with fallback responses
- Hosting: Vercel

## Demo value

This project is designed to be easy to present:

- mocked mode gives you repeatable recommendation flows
- dashboard and chatbot stay synchronized
- recommendation accept/reject actions visibly update UI state
- observability and events help explain operational impact

## Status

Deployed and working:

- Frontend: [https://cloud-optimizer-mcp-frontend.vercel.app](https://cloud-optimizer-mcp-frontend.vercel.app)
- Backend: [https://cloud-optimizer-mcp-backend.vercel.app](https://cloud-optimizer-mcp-backend.vercel.app)
