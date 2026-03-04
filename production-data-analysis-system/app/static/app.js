const authForm = document.getElementById('auth-form');
const authMessage = document.getElementById('auth-message');
const appContent = document.getElementById('app-content');
const currentUserText = document.getElementById('current-user');

const form = document.getElementById('record-form');
const filterForm = document.getElementById('filter-form');
const formMessage = document.getElementById('form-message');
const summaryBox = document.getElementById('summary-box');
const vizTable = document.getElementById('viz-table');
const recordsTable = document.getElementById('records-table');
const trendChart = document.getElementById('trend-chart');
const lastUpdated = document.getElementById('last-updated');
const recordsState = document.getElementById('records-state');
const pageInfo = document.getElementById('page-info');

const TOKEN_KEY = 'pda_token';
const USER_KEY = 'pda_username';

const state = {
  token: localStorage.getItem(TOKEN_KEY) || '',
  username: localStorage.getItem(USER_KEY) || '',
  filters: { start_date: '', end_date: '', line_name: '', product_name: '' },
  page: 1,
  pageSize: 10,
  total: 0
};

async function apiRequest(url, options = {}) {
  const headers = options.headers || {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) throw new Error(await response.text());
  return response;
}

async function fetchJson(url, options = {}) {
  const response = await apiRequest(url, options);
  return response.json();
}

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== '' && v !== undefined && v !== null && query.set(k, v));
  return query.toString() ? `?${query.toString()}` : '';
}

function setAuthMessage(message, isError = false) {
  authMessage.className = `feedback ${isError ? 'error' : 'ok'}`;
  authMessage.textContent = message;
}

function setFormMessage(message, isError = false) {
  formMessage.className = `feedback ${isError ? 'error' : 'ok'}`;
  formMessage.textContent = message;
}

function setLastUpdated() {
  lastUpdated.textContent = `最近刷新：${new Date().toLocaleString('zh-CN')}`;
}

function applyAuthState() {
  if (!state.token) {
    appContent.classList.add('hidden');
    currentUserText.textContent = '未登录';
    return;
  }
  appContent.classList.remove('hidden');
  currentUserText.textContent = `当前用户：${state.username}`;
}

function saveAuth(token, username) {
  state.token = token;
  state.username = username;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, username);
  applyAuthState();
}

function clearAuth() {
  state.token = '';
  state.username = '';
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  applyAuthState();
}

function renderKpi(data) {
  summaryBox.innerHTML = `
    <article class="kpi"><div class="label">总产量</div><div class="value">${data.total_output}</div></article>
    <article class="kpi"><div class="label">不良总数</div><div class="value">${data.total_defect}</div></article>
    <article class="kpi"><div class="label">不良率</div><div class="value">${(data.defect_rate * 100).toFixed(2)}%</div></article>
    <article class="kpi"><div class="label">总成本</div><div class="value">¥ ${Number(data.total_cost).toLocaleString()}</div></article>
  `;
}

async function loadSummary() {
  const query = buildQuery({ start_date: state.filters.start_date, end_date: state.filters.end_date });
  const data = await fetchJson(`/statistics/summary${query}`);
  renderKpi(data);
}

function renderTrend(rows) {
  if (!rows.length) {
    trendChart.innerHTML = '<span class="muted">暂无可视化数据</span>';
    return;
  }
  const maxOutput = Math.max(...rows.map((row) => row.total_output), 1);
  trendChart.innerHTML = rows.slice(-14).map((row) => {
    const height = Math.max(12, Math.round((row.total_output / maxOutput) * 100));
    return `<div class="bar" title="${row.production_date}：${row.total_output}" style="height:${height}px"></div>`;
  }).join('');
}

async function loadVisualization() {
  const query = buildQuery({ start_date: state.filters.start_date, end_date: state.filters.end_date });
  const rows = await fetchJson(`/visualization/daily-output${query}`);
  renderTrend(rows);
  vizTable.innerHTML = rows.length
    ? rows.map((row) => `<tr><td>${row.production_date}</td><td>${row.total_output}</td><td>${row.total_defect}</td></tr>`).join('')
    : '<tr><td colspan="3" class="muted">暂无数据</td></tr>';
}

function toEditableButton(record) {
  const payload = encodeURIComponent(JSON.stringify(record));
  return `<button class="btn-secondary edit-btn" data-record="${payload}">编辑</button>`;
}

async function loadRecords() {
  recordsState.textContent = '记录加载中...';
  const query = buildQuery({ ...state.filters, page: state.page, page_size: state.pageSize });
  const res = await fetchJson(`/records${query}`);
  const rows = res.items;
  state.total = res.total;
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  pageInfo.textContent = `第 ${state.page} / ${totalPages} 页，共 ${state.total} 条`;
  recordsState.textContent = rows.length ? `当前页 ${rows.length} 条` : '无匹配记录';

  recordsTable.innerHTML = rows.length
    ? rows.map((r) => `<tr>
      <td>${r.id}</td><td>${r.production_date}</td><td>${r.line_name}</td><td>${r.product_name}</td>
      <td>${r.output_quantity}</td><td>${r.defect_quantity}</td><td>${r.unit_cost}</td><td>${r.note || ''}</td>
      <td class="actions-cell">${toEditableButton(r)}<button data-id="${r.id}" class="delete-btn">删除</button></td>
    </tr>`).join('')
    : '<tr><td colspan="9" class="muted">筛选结果为空</td></tr>';

  document.querySelectorAll('.delete-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm(`确定删除记录 #${btn.dataset.id} 吗？`)) return;
      try {
        await apiRequest(`/records/${btn.dataset.id}`, { method: 'DELETE' });
        setFormMessage(`记录 #${btn.dataset.id} 已删除`);
        await refreshAll();
      } catch (error) {
        setFormMessage(`删除失败：${error.message}`, true);
      }
    });
  });

  document.querySelectorAll('.edit-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const record = JSON.parse(decodeURIComponent(btn.dataset.record));
      const output = prompt('修改产量', record.output_quantity);
      if (output === null) return;
      const defect = prompt('修改不良数', record.defect_quantity);
      if (defect === null) return;
      const note = prompt('修改备注', record.note || '');
      if (note === null) return;

      try {
        await apiRequest(`/records/${record.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ output_quantity: Number(output), defect_quantity: Number(defect), note })
        });
        setFormMessage(`记录 #${record.id} 更新成功`);
        await refreshAll();
      } catch (error) {
        setFormMessage(`更新失败：${error.message}`, true);
      }
    });
  });
}

async function refreshAll() {
  if (!state.token) return;
  await Promise.all([loadSummary(), loadVisualization(), loadRecords()]);
  setLastUpdated();
}

async function downloadReport(url, filename) {
  const response = await apiRequest(url);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}

authForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const username = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value;

  try {
    const data = await fetchJson('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    saveAuth(data.access_token, data.username);
    setAuthMessage(`登录成功，有效期至：${new Date(data.expires_at).toLocaleString('zh-CN')}`);
    await refreshAll();
  } catch (error) {
    setAuthMessage(`登录失败：${error.message}`, true);
  }
});

document.getElementById('register-btn').addEventListener('click', async () => {
  const username = document.getElementById('auth-username').value.trim();
  const password = document.getElementById('auth-password').value;

  try {
    const data = await fetchJson('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    saveAuth(data.access_token, data.username);
    setAuthMessage(`注册成功并已登录，有效期至：${new Date(data.expires_at).toLocaleString('zh-CN')}`);
    await refreshAll();
  } catch (error) {
    setAuthMessage(`注册失败：${error.message}`, true);
  }
});

document.getElementById('logout-btn').addEventListener('click', async () => {
  try {
    if (state.token) await apiRequest('/auth/logout', { method: 'POST' });
  } finally {
    clearAuth();
    setAuthMessage('已退出登录');
  }
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    production_date: document.getElementById('production_date').value,
    line_name: document.getElementById('line_name').value.trim(),
    product_name: document.getElementById('product_name').value.trim(),
    output_quantity: Number(document.getElementById('output_quantity').value),
    defect_quantity: Number(document.getElementById('defect_quantity').value),
    unit_cost: Number(document.getElementById('unit_cost').value),
    note: document.getElementById('note').value.trim()
  };

  try {
    await apiRequest('/production-data', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    form.reset();
    document.getElementById('defect_quantity').value = 0;
    setFormMessage('提交成功');
    state.page = 1;
    await refreshAll();
  } catch (error) {
    setFormMessage(`提交失败：${error.message}`, true);
  }
});

filterForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  state.filters.start_date = document.getElementById('filter_start_date').value;
  state.filters.end_date = document.getElementById('filter_end_date').value;
  state.filters.line_name = document.getElementById('filter_line_name').value.trim();
  state.filters.product_name = document.getElementById('filter_product_name').value.trim();
  state.page = 1;
  await refreshAll();
});

document.getElementById('reset-filter').addEventListener('click', async () => {
  filterForm.reset();
  state.filters = { start_date: '', end_date: '', line_name: '', product_name: '' };
  state.page = 1;
  await refreshAll();
});

document.getElementById('prev-page').addEventListener('click', async () => {
  if (state.page <= 1) return;
  state.page -= 1;
  await loadRecords();
});

document.getElementById('next-page').addEventListener('click', async () => {
  const totalPages = Math.max(1, Math.ceil(state.total / state.pageSize));
  if (state.page >= totalPages) return;
  state.page += 1;
  await loadRecords();
});

document.getElementById('refresh-summary').addEventListener('click', loadSummary);
document.getElementById('refresh-records').addEventListener('click', loadRecords);
document.getElementById('refresh-all').addEventListener('click', refreshAll);

document.getElementById('download-json').addEventListener('click', async () => {
  try {
    await downloadReport('/reports/daily', 'daily-report.json');
  } catch (error) {
    setFormMessage(`下载失败：${error.message}`, true);
  }
});

document.getElementById('download-csv').addEventListener('click', async () => {
  try {
    await downloadReport('/reports/daily/csv', 'daily-report.csv');
  } catch (error) {
    setFormMessage(`下载失败：${error.message}`, true);
  }
});

async function init() {
  applyAuthState();
  if (!state.token) return;

  try {
    const me = await fetchJson('/auth/me');
    state.username = me.username;
    localStorage.setItem(USER_KEY, me.username);
    applyAuthState();
    await refreshAll();
  } catch (error) {
    clearAuth();
    setAuthMessage('登录已过期，请重新登录', true);
  }
}

init();
