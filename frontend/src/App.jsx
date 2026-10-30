import React, { useCallback, useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const KEY = 'dev-secret-change-me';

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-API-Key': KEY, ...(options.headers || {}) }
  });
  if (!response.ok) throw new Error((await response.json()).detail || `HTTP ${response.status}`);
  return response.json();
}

function Stat({ label, value, tone }) {
  return <div className="stat"><span>{label}</span><strong className={tone || ''}>{value ?? '—'}</strong></div>;
}

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [error, setError] = useState('');
  const [taskType, setTaskType] = useState('send_email');
  const [payload, setPayload] = useState('{"to":"demo@example.com","subject":"Order confirmed"}');
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [j, m] = await Promise.all([request('/jobs'), request('/metrics')]);
      setJobs(j); setMetrics(m); setError('');
    } catch (e) { setError(`${e.message}. Is the API running?`); }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [refresh]);

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      await request('/jobs', { method: 'POST', body: JSON.stringify({
        task_type: taskType, payload: JSON.parse(payload), priority: 5, max_attempts: 3
      }), headers: { 'Idempotency-Key': `ui-${crypto.randomUUID()}` } });
      await refresh();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  return <main className="shell">
    <header className="topbar">
      <div className="brand"><div className="logo">P</div><div><b>PulseQ</b><small>JOB OPERATIONS CENTER</small></div></div>
      <div className="live"><i /> LIVE SYSTEM OVERVIEW <button onClick={refresh}>↻ Refresh</button></div>
    </header>

    <section className="intro">
      <div><p className="eyebrow">DISTRIBUTED WORK PROCESSING</p><h1>Queue intelligence<span>.</span></h1>
        <p className="sub">Observe, dispatch and understand background workloads across your worker fleet.</p></div>
      <div className="api-pill"><i /> API CONNECTED WHEN HEALTHY</div>
    </section>

    {error && <div className="error">{error}</div>}

    <section className="stats">
      <Stat label="TOTAL JOBS" value={metrics.total}/>
      <Stat label="QUEUED" value={metrics.queued} tone="blue"/>
      <Stat label="RUNNING" value={metrics.running} tone="violet"/>
      <Stat label="SUCCEEDED" value={metrics.succeeded} tone="green"/>
      <Stat label="RETRYING" value={metrics.retrying} tone="amber"/>
      <Stat label="DEAD LETTER" value={metrics.dead_letter} tone="red"/>
    </section>

    <section className="content-grid">
      <div className="panel create">
        <div className="panel-head"><div><p className="eyebrow">DISPATCH CENTER</p><h2>Create a job</h2></div><span className="tag">NEW TASK</span></div>
        <form onSubmit={submit}>
          <label>Task handler</label>
          <select value={taskType} onChange={e => setTaskType(e.target.value)}>
            <option value="send_email">send_email · Simulated email</option>
            <option value="generate_report">generate_report · Report task</option>
            <option value="demo_fail">demo_fail · Retry / DLQ demo</option>
          </select>
          <label>JSON payload</label>
          <textarea value={payload} onChange={e => setPayload(e.target.value)} rows="6" spellCheck="false"/>
          <button className="primary" disabled={busy}>{busy ? 'Dispatching…' : '＋ Dispatch job'}</button>
        </form>
        <p className="hint">Demo handlers run locally. No real emails are sent.</p>
      </div>

      <div className="panel jobs-panel">
        <div className="panel-head"><div><p className="eyebrow">EXECUTION STREAM</p><h2>Recent jobs</h2></div><span className="tag">{jobs.length} RECORDS</span></div>
        <div className="table-wrap"><table><thead><tr><th>JOB / HANDLER</th><th>STATUS</th><th>ATTEMPTS</th><th>CREATED</th></tr></thead>
          <tbody>{jobs.map(job => <tr key={job.id}>
            <td><b>{job.task_type}</b><small>{job.id.slice(0, 8)}…</small></td>
            <td><span className={`status ${job.status}`}>{job.status.replace('_',' ')}</span></td>
            <td>{job.attempts} / {job.max_attempts}</td>
            <td>{new Date(job.created_at).toLocaleTimeString()}</td>
          </tr>)}
          {!jobs.length && <tr><td colSpan="4" className="empty">No jobs yet. Dispatch your first task.</td></tr>}</tbody>
        </table></div>
      </div>
    </section>
    <footer><span>PulseQ <b>·</b> Distributed job processing reference implementation</span><span>API <a href={`${API}/docs`} target="_blank">OpenAPI docs ↗</a></span></footer>
  </main>;
}
