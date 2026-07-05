```markdown
# 🔥 Chaos Platform — Resilience Validation as a Service

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-✓-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-✓-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Grafana-✓-F46800?style=for-the-badge&logo=grafana&logoColor=white)](https://grafana.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**A platform for controlled infrastructure destruction with automated resilience validation**

[Architecture](#-architecture) •
[Quick Start](#-quick-start) •
[Examples](#-experiment-examples) •
[Documentation](#-documentation) •
[Roadmap](#-roadmap)

</div>

---

## 📖 About

**The Problem:** Teams configure monitoring, alerting, and auto-healing but never validate them under real stress. The first production incident reveals broken alerts, missing runbooks, and recovery that simply doesn't work.

**The Solution:** A platform that methodically breaks your infrastructure on schedule, measures system response, and proves (or disproves) that your SRE stack actually works.

### Key Features

- ✅ **Steady State Hypothesis** — system health validation via PromQL before any chaos injection
- ✅ **12+ Chaos Modules** — CPU, memory, disk, network, DNS, processes, Docker, HTTP flood
- ✅ **Real-time Monitoring** — WebSocket dashboard with live metrics during attacks
- ✅ **Auto-Rollback** — chaos auto-halts when degradation exceeds defined thresholds
- ✅ **GameDays Scheduler** — recurring tests via Cron expressions (every Monday at 9 AM)
- ✅ **REST API** — CI/CD integration (Jenkins, GitLab CI, GitHub Actions)
- ✅ **Notifications** — Telegram and Slack alerts with experiment results
- ✅ **Reports** — HTML/PDF with before/after comparison and PASS/FAIL verdict

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CHAOS CONTROL PLANE                       │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │   FastAPI    │  │   Scheduler   │  │  Hypothesis      │  │
│  │   REST API   │  │   (Cron)      │  │  Engine          │  │
│  │   + WebSocket│  │               │  │  (PromQL)        │  │
│  └──────┬───────┘  └───────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │            │
│  ┌──────┴──────────────────┴────────────────────┴─────────┐  │
│  │              CHAOS ORCHESTRATOR                        │  │
│  │  • Chaos module execution                             │  │
│  │  • Real-time metrics monitoring                       │  │
│  │  • Auto-Rollback on threshold breach                  │  │
│  │  • Recovery verification                              │  │
│  │  • Result analysis & verdict                          │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│  ┌──────────────────────┼───────────────────────────────┐  │
│  │    Notifier          │    Prometheus Watcher         │  │
│  │    (Telegram/Slack)  │    (PromQL queries)           │  │
│  └──────────────────────┴───────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────────┐  ┌──────────┐
    │ Target 1 │   │  Prometheus  │  │ Grafana  │
    │  (SSH)   │   │   + Metrics  │  │  Dash    │
    └──────────┘   └──────┬───────┘  └──────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ AlertManager │
                   │  → Telegram  │
                   └──────────────┘
```

---

## 🚀 Quick Start

### Project layout

The repository is now organized into the following modules:

- backend/ for FastAPI services, orchestration, scheduling, and persistence
- modules/ for chaos injection implementations
- frontend/ for dashboard UI assets
- tests/ for unit and integration coverage
- grafana/ and docs/ for observability and documentation

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- SSH access to target servers
- Prometheus + Grafana (optional, for full functionality)

### Installation

```bash
# Clone the repository
git clone https://github.com/Monet0/chaos-platform.git
cd chaos-platform

# Install dependencies
pip install -r requirements.txt

# Copy and edit configuration
cp config.example.yaml config.yaml
vim config.yamls
```

### Full Stack with Docker Compose

```bash
# Spins up platform + Prometheus + Grafana + demo application
docker-compose up -d

# Verify it's running
curl http://localhost:8000/api/health

# Run your first experiment
curl -X POST http://localhost:8000/api/experiments/run \
  -H "Content-Type: application/json" \
  -d '{"name": "cpu_stress", "target": "demo-node-1"}'

# Open the dashboard
open http://localhost:8000/dashboard
```

### Manual Launch

```bash
# Plain Python
python main.py

# Or via Makefile
make run
make test
make report
```

---

## 📝 Configuration

`config.yaml` — the single source of truth for the entire platform:

```yaml
# === Target Servers ===
targets:
  staging-node-1:
    host: "10.0.1.100"
    user: "devops"
    key_path: "~/.ssh/id_rsa"
    labels:
      env: "staging"
      role: "api"

# === Steady State Hypothesis ===
hypothesis:
  prometheus_url: "http://prometheus:9090"
  checks:
    - name: "Error rate < 1%"
      promql: "rate(http_requests_total{status=~'5..'}[5m]) / rate(http_requests_total[5m])"
      operator: "lt"
      threshold: 0.01
    - name: "P99 latency < 500ms"
      promql: "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))"
      operator: "lt"
      threshold: 0.5
    - name: "API replicas >= 3"
      promql: "count(up{job='api'})"
      operator: "gt"
      threshold: 2

# === Chaos Experiments ===
experiments:
  cpu_stress:
    name: "CPU Spike"
    description: "Stresses all CPU cores to 90%"
    command: "stress --cpu $(nproc) --timeout {duration}"
    default_duration: 120
    max_degradation:
      error_rate: 0.05
      latency_ms: 2000
  
  disk_fill:
    name: "Disk Fill"
    description: "Fills disk to 80% capacity"
    command: "dd if=/dev/zero of={path} bs=1M count={size_mb}"
    default_duration: 60
    params:
      path: "/tmp/chaos_fill"
      size_mb: 5120
  
  network_latency:
    name: "Network Latency"
    description: "Adds 200ms delay on network interface"
    command: "tc qdisc add dev eth0 root netem delay 200ms"
    cleanup: "tc qdisc del dev eth0 root"

# === GameDays Schedule ===
schedules:
  - name: "Weekly Chaos Monday"
    cron: "0 9 * * 1"     # Every Monday at 9:00 AM
    experiment: "cpu_stress"
    target: "staging-node-1"
    
  - name: "Daily Pod Kill"
    cron: "0 */6 * * *"   # Every 6 hours
    experiment: "process_kill"
    target: "staging-node-1"

# === Notifications ===
notifications:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "${TELEGRAM_CHAT_ID}"
  slack:
    webhook: "${SLACK_WEBHOOK_URL}"
```

---

## 💥 Experiment Examples

### CPU Stress

```bash
curl -X POST http://localhost:8000/api/experiments/run \
  -d '{"name": "cpu_stress", "target": "staging-node-1", "duration_override": 60}'
```

**Result:**
- CPU: 12% → 94%
- Latency P99: 120ms → 350ms
- Error rate: 0.1% → 0.3%
- Verdict: **PASS** — system remained resilient

### Disk Fill with Auto-Rollback

```bash
curl -X POST http://localhost:8000/api/experiments/run \
  -d '{"name": "disk_fill", "target": "staging-node-1", "params": {"size_mb": 10240}}'
```

**Result:**
- Disk: 23% → 91% → AUTO-ROLLBACK triggered at 92%
- Error rate exceeded 5% threshold → chaos halted immediately
- Verdict: **DEGRADED** — system needs improvement

### HTTP Flood (Custom Module)

```bash
curl -X POST http://localhost:8000/api/experiments/run \
  -d '{"name": "http_flood", "target": "api-gateway-1", "params": {"url": "http://api:8080/health", "rps": 5000, "duration": 30}}'
```

**Result:**
- 150,000 requests in 30 seconds
- 0 errors
- Latency P99: 180ms
- Verdict: **PASS** — API Gateway scales correctly

---

## 🖥 Web Dashboard

Dashboard available at `http://localhost:8000/dashboard`

### Features:
- **Live Graphs** via WebSocket during chaos execution
- **Experiment List** with one-click launch
- **History** of all runs with verdicts
- **Steady State Status** — current system health
- **Real-time Log Stream**

![Dashboard Screenshot](docs/dashboard.png)

*Replace with your actual dashboard screenshot*

---

## 📊 Grafana Integration

Pre-built Grafana dashboard included (`grafana/chaos-dashboard.json`):

### Panels:
1. **HTTP Error Rate** — 5xx spikes during chaos
2. **P99 Latency** — response time degradation
3. **CPU/Memory Usage** — node resource pressure
4. **Disk Usage** — disk fill progression
5. **Recovery Timeline** — time to recover after each experiment

```bash
# Import dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/chaos-dashboard.json
```

---

## 🔧 CLI & Makefile

```bash
make help           # Show all available commands
make run            # Launch the platform
make test           # Run tests
make docker-build   # Build Docker image
make docker-up      # Spin up full stack
make lint           # Run code linters
make report         # Generate HTML report
```

---

## 🧪 Testing

```bash
# Unit tests
pytest tests/ -v --cov=backend --cov=modules

# Integration test (requires Prometheus)
pytest tests/integration/ -v -m integration

# Platform smoke test
python -m pytest tests/test_smoke.py
```

---

## 📁 Project Structure

```
chaos-platform/
├── backend/
│   ├── main.py                 # FastAPI + WebSocket server
│   ├── orchestrator.py         # Chaos orchestration engine
│   ├── hypothesis.py           # Steady State Hypothesis validator
│   ├── scheduler.py            # Cron-based GameDays scheduler
│   ├── prometheus_watcher.py   # Prometheus API client
│   ├── notifier.py             # Telegram/Slack notifications
│   ├── models.py               # Pydantic data models
│   ├── db.py                   # SQLite experiment history
│   └── config.yaml             # Platform configuration
│
├── modules/                    # Chaos injection modules
│   ├── cpu_stress.py           # CPU stress
│   ├── disk_fill.py            # Disk capacity exhaustion
│   ├── memory_stress.py        # Memory leak simulation
│   ├── network_latency.py      # Network delay injection (tc)
│   ├── packet_loss.py          # Packet loss simulation
│   ├── dns_chaos.py            # DNS resolution corruption
│   ├── process_kill.py         # Process termination
│   ├── docker_kill.py          # Container termination
│   ├── http_flood.py           # HTTP DDoS simulation
│   └── iptables_block.py       # Port blocking via iptables
│
├── frontend/
│   ├── app.py                  # Streamlit/HTML dashboard
│   ├── templates/
│   │   └── dashboard.html
│   └── static/
│       ├── dashboard.js        # WebSocket client
│       └── style.css
│
├── tests/
│   ├── unit/
│   │   ├── test_hypothesis.py
│   │   ├── test_orchestrator.py
│   │   └── test_modules.py
│   ├── integration/
│   │   └── test_full_cycle.py
│   └── fixtures/
│
├── grafana/
│   ├── chaos-dashboard.json    # Pre-built Grafana dashboard
│   └── datasources/
│
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   └── screenshots/
│
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── requirements.txt
└── README.md
```

---

## 🎯 Roadmap

- [x] Steady State Hypothesis via PromQL
- [x] Auto-Rollback on degradation
- [x] WebSocket real-time dashboard
- [x] Telegram/Slack notifications
- [x] GameDays Cron Scheduler
- [x] REST API for CI/CD integration
- [ ] Chaos Agent on nodes (gRPC instead of SSH)
- [ ] Kubernetes Operator (CRD for ChaosExperiment)
- [ ] SLO-based Chaos (auto-escalation of chaos intensity)
- [ ] Integration with LitmusChaos and Chaos Mesh
- [ ] ChaosHub — library of ready-to-use experiments
- [ ] A/B Comparison (production vs canary during chaos)
- [ ] ML-based recovery time prediction

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License — do whatever you want, just attribute the author.

---

## 👤 Author

**Maksym** — DevOps Engineer

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ManeT0)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/maksym-netrebskyi-69bb993a4)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/Monet0yy)

---

## ⭐ Support the Project

If this project helped you or you find it useful:

- Give it a **star** ⭐ on GitHub
- Share it with your colleagues
- Spread the word on social media

---

<div align="center">

*"Chaos doesn't cause problems. Chaos reveals problems."*

</div>
```
