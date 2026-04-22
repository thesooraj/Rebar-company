{% extends "base.html" %}
{% block title %}WiFi Settings — Admin{% endblock %}
{% block body %}
<style>
  .page-header { margin-bottom: 20px; }
  .page-header h1 { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 2rem; letter-spacing: 0.04em; }
  .admin-nav { display: flex; gap: 10px; margin-bottom: 28px; flex-wrap: wrap; }
  .admin-nav a { padding: 9px 20px; border-radius: var(--radius); font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.05em; text-transform: uppercase; text-decoration: none; border: 1px solid var(--border); color: var(--muted); transition: all 0.15s; }
  .admin-nav a:hover, .admin-nav a.active { background: var(--blue); color: #fff; border-color: var(--blue); }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .field { margin-bottom: 16px; }
  .field label { display: block; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin-bottom: 7px; }
  .field input, .field select { width: 100%; background: var(--surface2); border: 1px solid var(--border); border-radius: var(--radius); padding: 11px 14px; font-family: 'Barlow', sans-serif; font-size: 0.95rem; color: var(--text); outline: none; }
  .field input:focus, .field select:focus { border-color: var(--blue-light); }
  .field select option { background: var(--surface2); }
  .status-row { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--border); }
  .status-row:last-child { border-bottom: none; }
  .status-label { font-size: 0.85rem; color: var(--muted); }
  .status-value { font-weight: 600; font-size: 0.9rem; }
  @media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
<main>
  <div class="page-header">
    <h1>WiFi Lock Settings</h1>
    <p style="color:var(--muted);font-size:0.9rem;margin-top:4px;">Control office WiFi clock-in restriction</p>
  </div>

  <div class="admin-nav">
    <a href="{{ url_for('admin_home') }}">Overview</a>
    <a href="{{ url_for('admin_employees') }}">Employees</a>
    <a href="{{ url_for('admin_timesheets') }}">Timesheets</a>
    <a href="{{ url_for('admin_announcements') }}">Announcements</a>
    <a href="{{ url_for('admin_reports') }}">Reports</a>
    <a href="{{ url_for('admin_documents') }}">Documents</a>
    <a href="{{ url_for('admin_wifi') }}" class="active">WiFi</a>
    <a href="{{ url_for('dashboard') }}">← Dashboard</a>
  </div>

  {% for cat, msg in get_flashed_messages(with_categories=True) %}
  <div class="flash {{ cat }}" style="margin-bottom:16px;">{{ msg }}</div>
  {% endfor %}

  <div class="grid-2">
    <!-- Settings form -->
    <div class="card">
      <div class="card-title">⚙️ WiFi Lock Configuration</div>
      <form method="POST" action="{{ url_for('admin_wifi') }}">
        <div class="field">
          <label>WiFi Lock</label>
          <select name="wifi_lock_enabled">
            <option value="0" {% if not wifi_status.enabled %}selected{% endif %}>Disabled — anyone can clock in</option>
            <option value="1" {% if wifi_status.enabled %}selected{% endif %}>Enabled — must be on office WiFi</option>
          </select>
        </div>
        <div class="field">
          <label>Office WiFi Name (SSID)</label>
          <input type="text" name="office_ssid" value="{{ wifi_status.office_ssid }}"
                 placeholder="e.g. RebarCompany-Office" />
        </div>
        <button type="submit" class="btn btn-orange" style="width:100%">Save Settings</button>
      </form>
    </div>

    <!-- Current status -->
    <div class="card">
      <div class="card-title">📡 Current WiFi Status</div>
      <div class="status-row">
        <span class="status-label">WiFi Lock</span>
        <span class="status-value">
          {% if wifi_status.enabled %}
            <span class="badge badge-orange">Enabled</span>
          {% else %}
            <span class="badge badge-green">Disabled</span>
          {% endif %}
        </span>
      </div>
      <div class="status-row">
        <span class="status-label">Office SSID</span>
        <span class="status-value">{{ wifi_status.office_ssid or '— not set —' }}</span>
      </div>
      <div class="status-row">
        <span class="status-label">Current Network</span>
        <span class="status-value">{{ wifi_status.current_ssid or '— not detected —' }}</span>
      </div>
      <div class="status-row">
        <span class="status-label">Clock-in Allowed</span>
        <span class="status-value">
          {% if wifi_status.on_office_wifi %}
            <span class="badge badge-green">✅ Yes</span>
          {% else %}
            <span class="badge badge-red">❌ No</span>
          {% endif %}
        </span>
      </div>

      <div style="margin-top:20px;padding:14px;background:var(--surface2);border-radius:var(--radius);font-size:0.85rem;color:var(--muted);line-height:1.6;">
        <strong style="color:var(--text)">How it works:</strong><br>
        When enabled, employees can only clock in when their device is connected to the office WiFi network. Clock-out is always allowed regardless of network.
      </div>
    </div>
  </div>
</main>
{% endblock %}