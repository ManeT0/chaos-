**Here's a polished, professional, and visually appealing English version of your README.md:**

# 🔥 Chaos Platform — Resilience Validation as a Service

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-✓-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-✓-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Grafana-✓-F46800?style=for-the-badge&logo=grafana&logoColor=white)](https://grafana.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Controlled chaos. Automated resilience validation. Real confidence in production.**

[Architecture](#-architecture) •
[Quick Start](#-quick-start) •
[Examples](#-experiment-examples) •
[Documentation](#-documentation) •
[Roadmap](#-roadmap)

</div>

---

## 📖 About

**The Problem**  
Teams invest heavily in monitoring, alerting, and auto-healing — yet never truly test them under stress. The first real production incident becomes a painful discovery of broken alerts, missing runbooks, and slow recovery.

**The Solution**  
**Chaos Platform** systematically breaks your infrastructure on schedule, measures how your system responds, and proves whether your SRE practices actually work.

### ✨ Key Features

- ✅ **Steady State Hypothesis** — PromQL-based health validation before chaos injection
- ✅ **12+ Chaos Modules** — CPU, memory, disk, network, DNS, processes, Docker, HTTP flood, and more
- ✅ **Real-time Monitoring** — Live WebSocket dashboard with metrics during experiments
- ✅ **Auto-Rollback** — Automatically halts chaos when degradation exceeds thresholds
- ✅ **Role-Based Access Control (RBAC)** — Secure API and dashboard with JWT auth (Admin/Viewer)
- ✅ **Chaos Agent (Go)** — Lightweight daemon for executing chaos securely without SSH
- ✅ **Secrets Management** — Resolve env vars & HashiCorp Vault secrets dynamically
- ✅ **GameDays Scheduler** — Recurring tests using Cron expressions
- ✅ **REST API** — Seamless CI/CD integration (GitHub Actions, GitLab CI, Jenkins)
- ✅ **Notifications** — Telegram & Slack alerts with experiment results
- ✅ **Reports** — Professional HTML/PDF reports with before/after comparison and PASS/FAIL verdict

---

## 🏗 Architecture

```mermaid
flowchart TD
    A[Chaos Control Plane] --> B[FastAPI + WebSocket]
    A --> C[Cron Scheduler]
    A --> D[Hypothesis Engine]
    B --> E[Chaos Orchestrator]
    E --> F[Chaos Agent (Go)]
    E --> G[Prometheus Watcher]
    E --> H[Notifier]
    F --> I[Target Systems]
    G --> J[Prometheus + Grafana]
```

---

## 🚀 Quick Start

### 1-Click Demo Deploy
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
*(Requires connecting your repo to Render)*

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Prometheus + Grafana (recommended)
- Go 1.21+ (for Chaos Agent)

### Installation

```bash
# Clone the repository
git clone https://github.com/ManeT0/chaos-.git
cd chaos-

# Install dependencies
pip install -r requirements.txt

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your targets, Prometheus URL, notifications, etc.
```

### Run with Docker Compose (Recommended)

```bash
docker compose up -d
```

### Run Chaos Agent
Deploy the lightweight agent to your target machines to avoid granting SSH access to the control plane.
```bash
cd agent
go build -o chaos-agent main.go
AGENT_TOKEN="your-token" ALLOWED_IPS="10.0.0.5" ./chaos-agent
```

### API Examples

```bash
# Check health
curl http://localhost:8000/api/health

# Authenticate
curl -X POST http://localhost:8000/api/auth/token \
  -d "username=admin&password=admin_password"

# Run first experiment
curl -X POST http://localhost:8000/api/experiments/run \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "cpu_stress", "target": "demo-node-1"}'
```

Open the dashboard: **http://localhost:8000/dashboard**

---

## 📝 Configuration (`config.yaml`)

```yaml
targets:
  staging-node-1:
    host: "10.0.1.100"
    user: "devops"
    key_path: "~/.ssh/id_rsa"
    labels:
      env: "staging"
      role: "api"

hypothesis:
  prometheus_url: "http://prometheus:9090"
  checks:
    - name: "Error rate < 1%"
      promql: "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m])"
      operator: "lt"
      threshold: 0.01

experiments:
  cpu_stress:
    name: "CPU Spike"
    command: "stress --cpu $(nproc) --timeout {duration}"
    default_duration: 120
    max_degradation:
      error_rate: 0.05

schedules:
  - name: "Weekly Chaos Monday"
    cron: "0 9 * * 1"
    experiment: "cpu_stress"
    target: "staging-node-1"

notifications:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
```

---

## 💥 Experiment Examples

### CPU Stress
```bash
curl -X POST http://localhost:8000/api/experiments/run \
  -d '{"name": "cpu_stress", "target": "staging-node-1", "duration_override": 60}'
```

**Expected Result:** System stays resilient → **PASS**

### Disk Fill (with Auto-Rollback)
Triggers rollback when thresholds are breached.

### HTTP Flood
Simulates traffic spikes against your API Gateway.

---

## 🖥 Web Dashboard

Live dashboard available at `/dashboard`

**Features:**
- Real-time graphs via WebSocket
- One-click experiment launch
- Full experiment history with verdicts
- Live log streaming
- Steady State health overview

*(Add screenshot here: `docs/dashboard.png`)*

---

## 📊 Grafana Integration

Pre-built dashboard included in `grafana/chaos-dashboard.json`

---

## 🔧 Makefile Commands

```bash
make help          # Show all commands
make run           # Start the platform
make docker-up     # Full stack with Prometheus + Grafana
make test          # Run tests
make lint          # Code quality
make report        # Generate HTML report
```

---

## 🧪 Testing

```bash
pytest tests/ -v --cov=backend
```

---

## 📁 Project Structure

```
chaos-platform/
├── backend/           # FastAPI, orchestrator, scheduler
├── modules/           # Individual chaos injection modules
├── frontend/          # Dashboard (Streamlit/HTML + JS)
├── tests/             # Unit + integration tests
├── grafana/           # Pre-built dashboards
├── docs/              # Additional documentation
├── config.example.yaml
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## 🎯 Roadmap

- [x] Steady State Hypothesis
- [x] Auto-Rollback & real-time monitoring
- [x] WebSocket dashboard
- [x] Notifications & reporting
- [x] Lightweight Chaos Agent (gRPC)
- [x] Kubernetes Operator
- [x] Integration with Chaos Mesh / LitmusChaos
- [ ] SLO-driven chaos intensity
- [ ] ML-based recovery prediction

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

## 👤 Author

**Maksym** — DevOps Engineer

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ManeT0)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/maksym-netrebskyi-69bb993a4)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/Monet0yy)

---

<div align="center">
  <strong>"Chaos doesn't cause problems. Chaos reveals problems."</strong>
</div>

---

⭐ **If you find this project useful, please star the repository!**


