let currentConfig = {};

async function loadConfig() {
  try {
    const response = await fetch('/api/config');
    currentConfig = await response.json();
    populateUI();
  } catch (error) {
    alert('Failed to load configuration: ' + error.message);
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });

  const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.getAttribute('onclick').includes(tabId));
  if (activeBtn) activeBtn.classList.add('active');
  
  const activeTab = document.getElementById(tabId);
  if (activeTab) activeTab.classList.add('active');
}

function populateUI() {
  // Safety
  document.getElementById('safety-dry-run').checked = currentConfig.safety.dry_run;
  document.getElementById('safety-max-duration').value = currentConfig.safety.max_duration_seconds;
  document.getElementById('safety-allow-dangerous').checked = currentConfig.safety.allow_dangerous_actions;
  document.getElementById('safety-auto-rollback').checked = currentConfig.safety.auto_rollback;
  document.getElementById('safety-audit-log').value = currentConfig.safety.audit_log_path;

  // Targets
  renderTargets();

  // Schedules
  renderSchedules();

  // Notifications
  const tg = currentConfig.notifications.telegram || {};
  document.getElementById('tg-token').value = tg.token || '';
  document.getElementById('tg-chat-id').value = tg.chat_id || '';

  const slack = currentConfig.notifications.slack || {};
  document.getElementById('slack-webhook').value = slack.webhook || '';
}

function renderTargets() {
  const container = document.getElementById('targets-list');
  container.innerHTML = '';
  
  const targetSelects = [document.getElementById('new-sched-target')];
  targetSelects.forEach(sel => {
    if (sel) sel.innerHTML = '';
  });

  Object.entries(currentConfig.targets).forEach(([name, target]) => {
    const div = document.createElement('div');
    div.className = 'target-item';
    div.innerHTML = `
      <div>
        <strong>${name}</strong> — ${target.user}@${target.host}
      </div>
      <button type="button" onclick="deleteTarget('${name}')">Delete</button>
    `;
    container.appendChild(div);

    targetSelects.forEach(sel => {
      if (sel) {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        sel.appendChild(opt);
      }
    });
  });
}

function addTarget() {
  const name = document.getElementById('new-target-name').value.trim();
  const host = document.getElementById('new-target-host').value.trim();
  const user = document.getElementById('new-target-user').value.trim();

  if (!name || !host || !user) {
    alert('All target fields are required.');
    return;
  }

  currentConfig.targets[name] = { host, user };
  document.getElementById('new-target-name').value = '';
  document.getElementById('new-target-host').value = '';
  document.getElementById('new-target-user').value = '';
  renderTargets();
}

function deleteTarget(name) {
  delete currentConfig.targets[name];
  renderTargets();
}

function renderSchedules() {
  const container = document.getElementById('schedules-list');
  container.innerHTML = '';

  currentConfig.schedules.forEach((sched, index) => {
    const div = document.createElement('div');
    div.className = 'schedule-item';
    div.innerHTML = `
      <div>
        <strong>${sched.name}</strong> (${sched.cron}): ${sched.experiment} on ${sched.target || 'default'}
      </div>
      <button type="button" onclick="deleteSchedule(${index})">Delete</button>
    `;
    container.appendChild(div);
  });
}

function addSchedule() {
  const name = document.getElementById('new-sched-name').value.trim();
  const cron = document.getElementById('new-sched-cron').value.trim();
  const experiment = document.getElementById('new-sched-experiment').value;
  const target = document.getElementById('new-sched-target').value;

  if (!name || !cron) {
    alert('Name and Cron expression are required.');
    return;
  }

  currentConfig.schedules.push({ name, cron, experiment, target });
  document.getElementById('new-sched-name').value = '';
  document.getElementById('new-sched-cron').value = '';
  renderSchedules();
}

function deleteSchedule(index) {
  currentConfig.schedules.splice(index, 1);
  renderSchedules();
}

async function saveSettings(event) {
  event.preventDefault();

  // Sync safety from UI
  currentConfig.safety.dry_run = document.getElementById('safety-dry-run').checked;
  currentConfig.safety.max_duration_seconds = parseInt(document.getElementById('safety-max-duration').value, 10);
  currentConfig.safety.allow_dangerous_actions = document.getElementById('safety-allow-dangerous').checked;
  currentConfig.safety.auto_rollback = document.getElementById('safety-auto-rollback').checked;
  currentConfig.safety.audit_log_path = document.getElementById('safety-audit-log').value;

  // Sync notifications from UI
  currentConfig.notifications = {
    telegram: {
      token: document.getElementById('tg-token').value.trim(),
      chat_id: document.getElementById('tg-chat-id').value.trim()
    },
    slack: {
      webhook: document.getElementById('slack-webhook').value.trim()
    }
  };

  try {
    const response = await fetch('/api/config/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(currentConfig)
    });

    const result = await response.json();
    if (result.status === 'ok') {
      alert('Settings saved successfully!');
      loadConfig();
    } else {
      alert('Failed to save settings: ' + result.message);
    }
  } catch (error) {
    alert('Error saving settings: ' + error.message);
  }
}

// Initial Load
document.addEventListener('DOMContentLoaded', loadConfig);
