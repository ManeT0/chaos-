/* ─── State ─────────────────────────────────────────────────────── */
const state = {
  experiments: [],
  targets: [],
  history: [],
  events: [],
  safety: null,
  running: false,
  wsRetryDelay: 1500,
};

/* ─── DOM refs ──────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const nodes = {
  connection:       $("connection-status"),
  hypothesisState:  $("hypothesis-state"),
  hypothesisPill:   $("hypothesis-pill"),
  safetyMode:       $("safety-mode"),
  runCount:         $("run-count"),
  launchStatus:     $("launch-status"),
  launchForm:       $("launch-form"),
  experimentSelect: $("experiment-select"),
  targetSelect:     $("target-select"),
  durationInput:    $("duration-input"),
  dryRunInput:      $("dry-run-input"),
  runBtn:           $("run-btn"),
  btnLabel:         $("run-btn").querySelector(".btn-label"),
  refreshButton:    $("refresh-button"),
  experimentsTable: $("experiments-table"),
  historyList:      $("history-list"),
  historyEmpty:     $("history-empty"),
  hypothesisList:   $("hypothesis-list"),
  eventFeed:        $("event-feed"),
  eventCount:       $("event-count"),
  toastContainer:   $("toast-container"),
};

/* ─── Status helpers ────────────────────────────────────────────── */
function statusVerdict(status) {
  const s = String(status || "").toLowerCase();
  if (["started", "dry_run", "completed", "pass", "ok"].includes(s))
    return { label: "PASS", cls: "pass" };
  if (["rejected", "aborted", "missing"].includes(s))
    return { label: "DEGRADED", cls: "degraded" };
  return { label: "FAIL", cls: "fail" };
}

function setPill(node, label, cls, pulse = false) {
  node.className = `status-pill ${cls}${pulse ? " pulse" : ""}`;
  node.textContent = label;
}

function eventClass(label) {
  const l = label.toLowerCase();
  if (l.includes("pass") || l.includes("completed") || l.includes("dry_run")) return "ev-pass";
  if (l.includes("start") || l.includes("queue") || l.includes("running")) return "ev-started";
  if (l.includes("fail") || l.includes("error") || l.includes("abort") || l.includes("reject")) return "ev-fail";
  return "ev-info";
}

/* ─── Formatting ────────────────────────────────────────────────── */
function formatTime(value) {
  if (!value) return "--";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function operatorSymbol(op) {
  return { lt: "<", lte: "≤", gt: ">", gte: "≥", eq: "=" }[op] || op;
}

/* ─── Fetch helper ──────────────────────────────────────────────── */
async function fetchJson(url, options = {}) {
  const token = sessionStorage.getItem("chaos_token");
  if (token) {
    options.headers = options.headers || {};
    options.headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(url, options);
  if (res.status === 401) {
    showLoginModal();
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
        const body = await res.json();
        if (body.detail) msg = body.detail;
    } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

/* ─── Toast system ──────────────────────────────────────────────── */
const TOAST_ICONS = { pass: "✅", fail: "❌", degraded: "⚠️", info: "ℹ️" };

function showToast(title, msg, type = "info", durationMs = 4000) {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `
    <span class="toast-icon">${TOAST_ICONS[type] || "ℹ️"}</span>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      ${msg ? `<div class="toast-msg">${msg}</div>` : ""}
    </div>`;
  nodes.toastContainer.appendChild(el);

  const dismiss = () => {
    el.classList.add("toast-out");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  };
  setTimeout(dismiss, durationMs);
  el.addEventListener("click", dismiss);
}

/* ─── Run-button state ──────────────────────────────────────────── */
function setRunning(running) {
  state.running = running;
  nodes.runBtn.disabled = running;
  nodes.runBtn.classList.toggle("running", running);
  nodes.btnLabel.textContent = running ? "Running…" : "Run";
}

/* ─── Render functions ──────────────────────────────────────────── */
function renderSelectors() {
  nodes.experimentSelect.innerHTML = state.experiments
    .map((e) => `<option value="${e.id}">${e.name}</option>`)
    .join("");
  nodes.targetSelect.innerHTML = state.targets
    .map((t) => `<option value="${t.id}">${t.id} (${t.host})</option>`)
    .join("");

  const first = state.experiments[0];
  nodes.durationInput.value = first?.default_duration ?? 30;
  nodes.dryRunInput.checked = Boolean(state.safety?.dry_run);
}

function renderExperiments() {
  if (!state.experiments.length) {
    nodes.experimentsTable.innerHTML =
      `<tr><td colspan="5" class="muted" style="text-align:center;padding:24px">No experiments configured</td></tr>`;
    return;
  }
  nodes.experimentsTable.innerHTML = state.experiments
    .map((exp) => {
      const lastRun = state.history.find((h) => h.experiment === exp.id);
      const verdict = statusVerdict(lastRun?.status ?? "missing");
      const riskBadge = exp.dangerous
        ? `<span class="status-pill fail" style="font-size:10px">Dangerous</span>`
        : `<span class="status-pill neutral" style="font-size:10px">Standard</span>`;
      return `
        <tr>
          <td><strong>${exp.name}</strong></td>
          <td>${exp.module}</td>
          <td>${exp.default_duration ?? "—"}s</td>
          <td>${riskBadge}</td>
          <td><span class="status-pill ${verdict.cls}">${verdict.label}</span></td>
        </tr>`;
    })
    .join("");
}

function renderHistory() {
  nodes.runCount.textContent = String(state.history.length);
  const hasItems = state.history.length > 0;
  nodes.historyEmpty.hidden = hasItems;

  if (!hasItems) { nodes.historyList.innerHTML = ""; return; }

  nodes.historyList.innerHTML = [...state.history]
    .reverse()
    .map((item) => {
      const verdict = statusVerdict(item.status);
      const duration = item.duration ? `${item.duration}s` : "—";
      const ts = formatTime(item.finished_at || item.started_at);
      const dryTag = item.dry_run ? ` <span class="status-pill neutral" style="font-size:10px">Dry</span>` : "";
      return `
        <li>
          <div>
            <strong>${item.experiment}${dryTag}</strong>
            <span>${item.target ?? "no target"} · ${duration} · ${ts}</span>
          </div>
          <span class="status-pill ${verdict.cls}">${verdict.label}</span>
        </li>`;
    })
    .join("");
}

function renderHypothesis(data) {
  const verdict = data.healthy
    ? { label: "PASS", cls: "pass" }
    : { label: "FAIL", cls: "fail" };

  nodes.hypothesisState.textContent = verdict.label;
  nodes.hypothesisState.style.color =
    verdict.cls === "pass" ? "var(--pass)" : "var(--fail)";
  setPill(nodes.hypothesisPill, verdict.label, verdict.cls, true);

  if (!data.checks || !data.checks.length) {
    nodes.hypothesisList.innerHTML =
      `<li class="muted" style="border:0;padding:12px 0">No checks configured</li>`;
    return;
  }

  nodes.hypothesisList.innerHTML = data.checks
    .map((check) => {
      const cv = check.passed
        ? { label: "PASS", cls: "pass" }
        : { label: "FAIL", cls: "fail" };
      const detail = check.operator
        ? `${operatorSymbol(check.operator)} ${check.threshold}`
        : "";
      const desc = check.description || check.error || "Steady-state check";
      return `
        <li>
          <div>
            <strong>${check.check ?? check.name ?? "Check"}</strong>
            <span>${desc}${detail ? ` · ${detail}` : ""}</span>
          </div>
          <span class="status-pill ${cv.cls}">${cv.label}</span>
        </li>`;
    })
    .join("");
}

function renderEvents() {
  nodes.eventCount.textContent = `${state.events.length} event${state.events.length !== 1 ? "s" : ""}`;
  nodes.eventFeed.innerHTML = [...state.events]
    .reverse()
    .map((ev) => {
      const cls = eventClass(ev.label);
      return `
        <li class="${cls}">
          <span class="ev-time">${formatTime(ev.time)}</span>
          <span class="ev-label">${ev.label}</span>
        </li>`;
    })
    .join("");
}

/* ─── Push event ────────────────────────────────────────────────── */
function pushEvent(label) {
  state.events.push({ label, time: new Date().toISOString() });
  state.events = state.events.slice(-30);
  renderEvents();
}

/* ─── Refresh all data ──────────────────────────────────────────── */
async function refreshDashboard() {
  const [experiments, targets, history, safety, hypothesis, user] = await Promise.all([
    fetchJson("/api/experiments"),
    fetchJson("/api/targets"),
    fetchJson("/api/experiments/history"),
    fetchJson("/api/platform/safety"),
    fetchJson("/api/hypothesis/status"),
    fetchJson("/api/auth/me").catch(() => null), // Catch error if not logged in
  ]);

  if (user && user.role === "viewer") {
    nodes.runBtn.disabled = true;
    nodes.runBtn.title = "Viewers cannot run experiments";
    nodes.launchForm.style.opacity = "0.6";
  } else {
    nodes.runBtn.disabled = state.running;
    nodes.runBtn.title = "";
    nodes.launchForm.style.opacity = "1";
  }

  state.experiments = experiments;
  state.targets = targets;
  state.history = history;
  state.safety = safety;

  nodes.safetyMode.textContent = safety.dry_run ? "Dry Run" : "Live";
  nodes.safetyMode.style.color = safety.dry_run ? "var(--degraded)" : "var(--pass)";

  renderSelectors();
  renderHistory();
  renderExperiments();
  renderHypothesis(hypothesis);
}

/* ─── Auto-refresh hypothesis every 30s ────────────────────────── */
setInterval(async () => {
  try {
    const h = await fetchJson("/api/hypothesis/status");
    renderHypothesis(h);
  } catch (_) { /* silent */ }
}, 30_000);


/* ─── WebSocket with exponential backoff ────────────────────────── */
function connectWebSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${proto}://${location.host}/ws`);

  socket.addEventListener("open", () => {
    nodes.connection.textContent = "Connected to event stream";
    nodes.connection.className = "connected";
    state.wsRetryDelay = 1500;
  });

  socket.addEventListener("message", async (ev) => {
    let payload;
    try { payload = JSON.parse(ev.data); } catch { return; }

    if (payload.type === "connected") {
      pushEvent(payload.message);
      return;
    }

    if (payload.type === "experiment_started") {
      pushEvent(`Started: ${payload.experiment}`);
      setPill(nodes.launchStatus, "Running…", "degraded", true);
      return;
    }

    if (payload.type === "experiment_completed") {
      const result = payload.result ?? {};
      const verdict = statusVerdict(result.status);
      pushEvent(`${verdict.label}: ${result.experiment ?? "experiment"}`);
      setPill(nodes.launchStatus, verdict.label, verdict.cls, verdict.cls === "pass");
      setRunning(false);

      const toastType = verdict.cls;
      const toastTitle = verdict.label === "PASS" ? "Experiment completed" : `Experiment ${verdict.label.toLowerCase()}`;
      showToast(toastTitle, `${result.experiment ?? ""}${result.dry_run ? " (dry run)" : ""}`, toastType);

      await refreshDashboard();
    }
  });

  socket.addEventListener("close", () => {
    nodes.connection.textContent = `Disconnected — reconnecting in ${(state.wsRetryDelay / 1000).toFixed(1)}s`;
    nodes.connection.className = "disconnected";
    pushEvent("Event stream disconnected");
    setTimeout(() => {
      state.wsRetryDelay = Math.min(state.wsRetryDelay * 1.5, 10_000);
      connectWebSocket();
    }, state.wsRetryDelay);
  });

  socket.addEventListener("error", () => socket.close());
}

/* ─── Event listeners ───────────────────────────────────────────── */
nodes.launchForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (state.running) return;

  const targetId = nodes.targetSelect.value;
  const targetConfig = state.targets.find(t => t.id === targetId);

  // Check for Prod Confirmation
  if (targetConfig && targetConfig.labels && targetConfig.labels.env === "prod") {
    showProdModal(targetId, () => {
      runExperiment(e).catch((err) => {
        setRunning(false);
        setPill(nodes.launchStatus, "FAIL", "fail");
        pushEvent(`Error: ${err.message}`);
        showToast("Error", err.message, "fail");
      });
    });
    return;
  }

  // Normal flow
  runExperiment(e).catch((err) => {
    setRunning(false);
    setPill(nodes.launchStatus, "FAIL", "fail");
    pushEvent(`Error: ${err.message}`);
    showToast("Error", err.message, "fail");
  });
});

nodes.refreshButton.addEventListener("click", () => {
  nodes.refreshButton.textContent = "↺ …";
  refreshDashboard()
    .then(() => { nodes.refreshButton.textContent = "↺ Refresh"; })
    .catch((err) => {
      nodes.refreshButton.textContent = "↺ Refresh";
      pushEvent(`Refresh failed: ${err.message}`);
    });
});

nodes.experimentSelect.addEventListener("change", () => {
  const sel = state.experiments.find((e) => e.id === nodes.experimentSelect.value);
  nodes.durationInput.value = sel?.default_duration ?? 30;
});

/* ─── Auth and Modals ───────────────────────────────────────────── */
function showLoginModal() {
  const modal = $("login-modal");
  modal.showModal();
}

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new URLSearchParams();
  formData.append("username", $("login-username").value);
  formData.append("password", $("login-password").value);

  try {
    const res = await fetch("/api/auth/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: formData.toString()
    });
    if (!res.ok) throw new Error("Invalid credentials");
    const data = await res.json();
    sessionStorage.setItem("chaos_token", data.access_token);
    $("login-modal").close();
    showToast("Logged in", "Successfully authenticated", "pass");
    location.reload();
  } catch (err) {
    showToast("Login Failed", err.message, "fail");
  }
});

let prodConfirmCallback = null;

function showProdModal(targetName, onConfirm) {
  const modal = $("prod-modal");
  $("prod-target-name-display").textContent = targetName;
  $("prod-confirm-input").value = "";
  $("prod-confirm-btn").disabled = true;
  prodConfirmCallback = onConfirm;
  modal.showModal();
}

$("prod-confirm-input").addEventListener("input", (e) => {
  const expected = $("prod-target-name-display").textContent;
  $("prod-confirm-btn").disabled = (e.target.value !== expected);
});

$("prod-cancel-btn").addEventListener("click", () => {
  $("prod-modal").close();
});

$("prod-confirm-form").addEventListener("submit", (e) => {
  e.preventDefault();
  if (prodConfirmCallback) {
    prodConfirmCallback();
  }
  $("prod-modal").close();
});

// Update runExperiment payload slightly for confirm_prod
async function runExperiment(event) {
  if (state.running) return;

  const targetId = nodes.targetSelect.value;
  const targetConfig = state.targets.find(t => t.id === targetId);
  const isProd = targetConfig && targetConfig.labels && targetConfig.labels.env === "prod";

  const payload = {
    name: nodes.experimentSelect.value,
    target: targetId,
    dry_run: nodes.dryRunInput.checked,
    confirm_prod: isProd // Inject confirmation flag if it was a prod target
  };
  const dur = Number(nodes.durationInput.value);
  if (dur > 0) payload.duration_override = dur;

  setRunning(true);
  setPill(nodes.launchStatus, "Queued", "degraded");

  await fetchJson("/api/experiments/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  pushEvent(`Queued: ${payload.name}`);
  showToast("Experiment queued", `${payload.name} → ${payload.target ?? "default target"}`, "info");
  setTimeout(refreshDashboard, 400);
}

/* ─── Bootstrap ─────────────────────────────────────────────────── */
refreshDashboard()
  .then(connectWebSocket)
  .catch((err) => {
    setPill(nodes.launchStatus, "FAIL", "fail");
    pushEvent(`Load failed: ${err.message}`);
    showToast("Load failed", err.message, "fail");
  });
