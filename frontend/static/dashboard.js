const state = {
  experiments: [],
  targets: [],
  history: [],
  events: [],
  safety: null,
};

const nodes = {
  connection: document.querySelector("#connection-status"),
  hypothesisState: document.querySelector("#hypothesis-state"),
  hypothesisPill: document.querySelector("#hypothesis-pill"),
  safetyMode: document.querySelector("#safety-mode"),
  runCount: document.querySelector("#run-count"),
  launchStatus: document.querySelector("#launch-status"),
  launchForm: document.querySelector("#launch-form"),
  experimentSelect: document.querySelector("#experiment-select"),
  targetSelect: document.querySelector("#target-select"),
  durationInput: document.querySelector("#duration-input"),
  dryRunInput: document.querySelector("#dry-run-input"),
  refreshButton: document.querySelector("#refresh-button"),
  experimentsTable: document.querySelector("#experiments-table"),
  historyList: document.querySelector("#history-list"),
  historyEmpty: document.querySelector("#history-empty"),
  hypothesisList: document.querySelector("#hypothesis-list"),
  eventFeed: document.querySelector("#event-feed"),
  eventCount: document.querySelector("#event-count"),
};

function statusVerdict(status) {
  const normalized = String(status || "").toLowerCase();
  if (["started", "dry_run", "completed", "pass", "ok"].includes(normalized)) {
    return { label: "PASS", className: "pass" };
  }
  if (["rejected", "aborted", "missing"].includes(normalized)) {
    return { label: "DEGRADED", className: "degraded" };
  }
  return { label: "FAIL", className: "fail" };
}

function setPill(node, label, className) {
  node.className = `status-pill ${className}`;
  node.textContent = label;
}

function formatTime(value) {
  if (!value) return "--";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function renderSelectors() {
  nodes.experimentSelect.innerHTML = state.experiments
    .map((experiment) => `<option value="${experiment.id}">${experiment.name}</option>`)
    .join("");
  nodes.targetSelect.innerHTML = state.targets
    .map((target) => `<option value="${target.id}">${target.id} (${target.host})</option>`)
    .join("");

  const selected = state.experiments[0];
  nodes.durationInput.value = selected?.default_duration || 30;
  nodes.dryRunInput.checked = Boolean(state.safety?.dry_run);
}

function renderExperiments() {
  nodes.experimentsTable.innerHTML = state.experiments
    .map((experiment) => {
      const lastRun = state.history.find((item) => item.experiment === experiment.id);
      const verdict = statusVerdict(lastRun?.status || "missing");
      return `
        <tr>
          <td><strong>${experiment.name}</strong></td>
          <td>${experiment.module}</td>
          <td>${experiment.default_duration}s</td>
          <td>${experiment.dangerous ? "Dangerous" : "Standard"}</td>
          <td><span class="status-pill ${verdict.className}">${verdict.label}</span></td>
        </tr>
      `;
    })
    .join("");
}

function renderHistory() {
  nodes.runCount.textContent = String(state.history.length);
  nodes.historyEmpty.hidden = state.history.length > 0;
  nodes.historyList.innerHTML = state.history
    .slice()
    .reverse()
    .map((item) => {
      const verdict = statusVerdict(item.status);
      return `
        <li>
          <div>
            <strong>${item.experiment}</strong>
            <span>${item.target || "no target"} · ${item.duration || "--"}s · ${formatTime(item.finished_at || item.started_at)}</span>
          </div>
          <span class="status-pill ${verdict.className}">${verdict.label}</span>
        </li>
      `;
    })
    .join("");
}

function renderHypothesis(data) {
  const verdict = data.healthy ? { label: "PASS", className: "pass" } : { label: "FAIL", className: "fail" };
  nodes.hypothesisState.textContent = verdict.label;
  setPill(nodes.hypothesisPill, verdict.label, verdict.className);

  if (!data.checks.length) {
    nodes.hypothesisList.innerHTML = '<li class="muted">No checks configured</li>';
    return;
  }

  nodes.hypothesisList.innerHTML = data.checks
    .map((check) => {
      const checkVerdict = check.passed
        ? { label: "PASS", className: "pass" }
        : { label: "FAIL", className: "fail" };
      return `
        <li>
          <div>
            <strong>${check.check}</strong>
            <span>${check.description || check.error || "Steady state check"}</span>
          </div>
          <span class="status-pill ${checkVerdict.className}">${checkVerdict.label}</span>
        </li>
      `;
    })
    .join("");
}

function renderEvents() {
  nodes.eventCount.textContent = `${state.events.length} events`;
  nodes.eventFeed.innerHTML = state.events
    .slice()
    .reverse()
    .map((event) => `<li><span>${formatTime(event.time)}</span><strong>${event.label}</strong></li>`)
    .join("");
}

function pushEvent(label) {
  state.events.push({ label, time: new Date().toISOString() });
  state.events = state.events.slice(-20);
  renderEvents();
}

async function refreshDashboard() {
  const [experiments, targets, history, safety, hypothesis] = await Promise.all([
    fetchJson("/api/experiments"),
    fetchJson("/api/targets"),
    fetchJson("/api/experiments/history"),
    fetchJson("/api/platform/safety"),
    fetchJson("/api/hypothesis/status"),
  ]);

  state.experiments = experiments;
  state.targets = targets;
  state.history = history;
  state.safety = safety;

  nodes.safetyMode.textContent = safety.dry_run ? "Dry run" : "Live";
  renderSelectors();
  renderHistory();
  renderExperiments();
  renderHypothesis(hypothesis);
}

async function runExperiment(event) {
  event.preventDefault();
  const payload = {
    name: nodes.experimentSelect.value,
    target: nodes.targetSelect.value,
    dry_run: nodes.dryRunInput.checked,
  };
  const duration = Number(nodes.durationInput.value);
  if (duration > 0) {
    payload.duration_override = duration;
  }

  setPill(nodes.launchStatus, "Queued", "degraded");
  await fetchJson("/api/experiments/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  pushEvent(`Queued ${payload.name}`);
  setTimeout(refreshDashboard, 400);
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

  socket.addEventListener("open", () => {
    nodes.connection.textContent = "Connected to event stream";
  });

  socket.addEventListener("message", async (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "connected") {
      pushEvent(payload.message);
      return;
    }
    if (payload.type === "experiment_started") {
      pushEvent(`Started ${payload.experiment}`);
      setPill(nodes.launchStatus, "Running", "degraded");
      return;
    }
    if (payload.type === "experiment_completed") {
      const result = payload.result;
      const verdict = statusVerdict(result.status);
      pushEvent(`${verdict.label} ${result.experiment}`);
      setPill(nodes.launchStatus, verdict.label, verdict.className);
      await refreshDashboard();
    }
  });

  socket.addEventListener("close", () => {
    nodes.connection.textContent = "Disconnected from event stream";
    pushEvent("Event stream disconnected");
    setTimeout(connectWebSocket, 1500);
  });
}

nodes.launchForm.addEventListener("submit", (event) => {
  runExperiment(event).catch((error) => {
    setPill(nodes.launchStatus, "FAIL", "fail");
    pushEvent(`Run failed: ${error.message}`);
  });
});

nodes.refreshButton.addEventListener("click", () => {
  refreshDashboard().catch((error) => pushEvent(`Refresh failed: ${error.message}`));
});

nodes.experimentSelect.addEventListener("change", () => {
  const selected = state.experiments.find((experiment) => experiment.id === nodes.experimentSelect.value);
  nodes.durationInput.value = selected?.default_duration || 30;
});

refreshDashboard()
  .then(connectWebSocket)
  .catch((error) => {
    setPill(nodes.launchStatus, "FAIL", "fail");
    pushEvent(`Load failed: ${error.message}`);
  });
