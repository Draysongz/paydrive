# PayDrive AI

## Description
Autonomous Accounts Payable engine that ingests invoices from local NAS directories, verifies them with AI-powered extraction and deterministic guardrails, and settles payments via PayPal or Web3 smart contracts — all running 100% on-premises.

## Category
Finance / Automation

## Requirements
- Docker & Docker Compose
- 2GB RAM minimum
- Network access for payment rail APIs (PayPal sandbox, EVM RPC)

## Installation
1. Copy the `paydrive/` directory to your NAS storage
2. Configure `.env` with your API keys
3. Run `docker-compose up -d`
4. Access dashboard at `http://<nas-ip>:3000`

## Volumes
- `/inbox` — Drop invoices (PDF, PNG, JPG) here for automatic processing
- `/data` — SQLite database and audit logs (persistent)

## Privacy
All invoice data stays on your local device. AI extraction calls are the only external network requests, and these can be eliminated by using the Ollama (local) AI provider.
