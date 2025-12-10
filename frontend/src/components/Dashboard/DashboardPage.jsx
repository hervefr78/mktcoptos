import React, { useEffect, useMemo, useState } from 'react';
import { API_BASE } from '../../config/api';
import { fetchJsonWithRetry } from '../../utils/fetchWithRetry';
import './DashboardPage.css';

const statusOptions = ['All', 'pending', 'running', 'completed', 'failed'];
const statusLabels = {
  pending: 'Queued',
  running: 'Generating',
  completed: 'Completed',
  failed: 'Needs attention',
};

const formatRelative = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

const TimelineChart = ({ data }) => {
  const maxValue = Math.max(
    1,
    ...data.flatMap((point) => [point.pending, point.running, point.completed])
  );

  return (
    <div className="timeline-chart">
      <div className="timeline-grid">
        {data.map((point) => (
          <div key={point.label} className="timeline-column">
            <div className="bar-group" aria-label={`${point.label} activity`}>
              <div className="bar pending" style={{ height: `${(point.pending / maxValue) * 100}%` }}>
                <span className="sr-only">{point.pending} queued</span>
              </div>
              <div className="bar running" style={{ height: `${(point.running / maxValue) * 100}%` }}>
                <span className="sr-only">{point.running} generating</span>
              </div>
              <div className="bar completed" style={{ height: `${(point.completed / maxValue) * 100}%` }}>
                <span className="sr-only">{point.completed} completed</span>
              </div>
            </div>
            <span className="timeline-label">{point.label}</span>
          </div>
        ))}
      </div>
      <div className="timeline-legend" aria-hidden>
        <span><span className="dot pending" />Queued</span>
        <span><span className="dot running" />Generating</span>
        <span><span className="dot completed" />Completed</span>
      </div>
    </div>
  );
};

const Sparkline = ({ values }) => {
  const points = useMemo(() => {
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = max - min || 1;
    const width = 80;
    const height = 28;
    return values
      .map((value, index) => {
        const x = (index / (values.length - 1 || 1)) * width;
        const y = height - ((value - min) / range) * height;
        return `${x},${y}`;
      })
      .join(' ');
  }, [values]);

  return (
    <svg className="sparkline" viewBox="0 0 80 28" role="img" aria-label="Trend sparkline">
      <polyline points={points} />
    </svg>
  );
};

const ChipFilterGroup = ({ label, options, selected, onChange, multi = false }) => (
  <div className="filter-group">
    <span className="filter-label">{label}</span>
    <div className="chip-row" role="list">
      {options.map((option) => {
        const isSelected = multi ? selected.includes(option) : selected === option;
        return (
          <button
            key={option}
            type="button"
            className={`chip ${isSelected ? 'active' : ''}`}
            onClick={() => onChange(option)}
            role="listitem"
          >
            {option}
          </button>
        );
      })}
    </div>
  </div>
);

const normalizeType = (type) => type || 'Uncategorized';
const normalizeModel = (model) => model || 'Unspecified model';

const DashboardPage = () => {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedCategories, setSelectedCategories] = useState([]);
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [selectedModel, setSelectedModel] = useState('All');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [historyData, statsData] = await Promise.all([
          fetchJsonWithRetry(`${API_BASE}/api/content-pipeline/history?limit=50`, { credentials: 'include' }),
          fetchJsonWithRetry(`${API_BASE}/api/content-pipeline/history/stats/summary`, { credentials: 'include' }),
        ]);

        setHistory(Array.isArray(historyData?.executions) ? historyData.executions : []);
        setStats(statsData || null);
        setError(null);
      } catch (err) {
        console.error('Failed to load dashboard data', err);
        setError('Unable to load pipeline data. Please check your connection or try again.');
        setHistory([]);
        setStats(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const categoryOptions = useMemo(() => {
    const categories = Array.from(new Set(history.map((item) => normalizeType(item.content_type))));
    return categories.length ? categories : ['Uncategorized'];
  }, [history]);

  const modelOptions = useMemo(() => {
    const models = Array.from(new Set(history.map((item) => normalizeModel(item.model_used))));
    return ['All', ...(models.length ? models : ['Unspecified model'])];
  }, [history]);

  useEffect(() => {
    if (categoryOptions.length && selectedCategories.length === 0) {
      setSelectedCategories(categoryOptions);
    }
  }, [categoryOptions, selectedCategories.length]);

  const toggleCategory = (category) => {
    setSelectedCategories((prev) =>
      prev.includes(category) ? prev.filter((item) => item !== category) : [...prev, category]
    );
  };

  const filteredHistory = useMemo(() => {
    return history.filter((item) => {
      const category = normalizeType(item.content_type);
      const model = normalizeModel(item.model_used);
      const matchesCategory = selectedCategories.length === 0 || selectedCategories.includes(category);
      const matchesStatus = selectedStatus === 'All' || item.status === selectedStatus;
      const matchesModel = selectedModel === 'All' || model === selectedModel;
      return matchesCategory && matchesStatus && matchesModel;
    });
  }, [history, selectedCategories, selectedStatus, selectedModel]);

  const categorySummary = useMemo(() => {
    const map = new Map();

    filteredHistory.forEach((item) => {
      const category = normalizeType(item.content_type);
      const record = map.get(category) || {
        category,
        total: 0,
        completed: 0,
        pending: 0,
        running: 0,
        failed: 0,
        topics: [],
        models: {},
        words: [],
      };

      record.total += 1;
      record.topics = record.topics.slice(0, 3);
      if (item.topic && !record.topics.includes(item.topic)) {
        record.topics = [item.topic, ...record.topics].slice(0, 3);
      }
      if (item.word_count) {
        record.words.push(item.word_count);
      }
      const model = normalizeModel(item.model_used);
      record.models[model] = (record.models[model] || 0) + 1;

      if (item.status === 'completed') record.completed += 1;
      if (item.status === 'pending') record.pending += 1;
      if (item.status === 'running') record.running += 1;
      if (item.status === 'failed') record.failed += 1;

      map.set(category, record);
    });

    return Array.from(map.values()).sort((a, b) => b.total - a.total);
  }, [filteredHistory]);

  const timelinePoints = useMemo(() => {
    const days = [...Array(7).keys()].map((offset) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - offset));
      const label = date.toLocaleDateString(undefined, { weekday: 'short' });
      const dateKey = date.toISOString().slice(0, 10);
      return { label, dateKey, pending: 0, running: 0, completed: 0 };
    });

    filteredHistory.forEach((item) => {
      const createdAt = item.created_at || item.started_at;
      if (!createdAt) return;
      const dateKey = new Date(createdAt).toISOString().slice(0, 10);
      const point = days.find((d) => d.dateKey === dateKey);
      if (!point) return;
      if (item.status === 'pending') point.pending += 1;
      if (item.status === 'running') point.running += 1;
      if (item.status === 'completed') point.completed += 1;
    });

    return days;
  }, [filteredHistory]);

  const kpiSparklines = timelinePoints.map((p) => p.completed || 0);

  const primaryKpis = useMemo(() => {
    const total = stats?.total_executions ?? filteredHistory.length;
    const completed = stats?.completed ?? filteredHistory.filter((h) => h.status === 'completed').length;
    const failed = stats?.failed ?? filteredHistory.filter((h) => h.status === 'failed').length;
    const avgWords = stats?.avg_word_count ?? Math.round(
      filteredHistory.reduce((sum, h) => sum + (h.word_count || 0), 0) /
        (filteredHistory.length || 1)
    );
    const avgDurationSeconds = stats?.avg_duration_seconds ?? 0;

    return [
      {
        label: 'Content generated',
        value: total,
        delta: `${completed} completed` + (failed ? ` • ${failed} needs attention` : ''),
        description: `Past ${stats?.period_days || 30} days of pipeline runs`,
        sparkline: kpiSparklines,
      },
      {
        label: 'Completion rate',
        value: total ? `${Math.round((completed / total) * 100)}%` : '0%',
        delta: failed ? `${failed} failed` : 'Healthy',
        description: 'Finished executions vs. total',
        sparkline: kpiSparklines,
      },
      {
        label: 'Avg word count',
        value: avgWords || '—',
        delta: 'Per completed piece',
        description: 'Based on stored final content metadata',
        sparkline: kpiSparklines,
      },
      {
        label: 'Avg duration',
        value: avgDurationSeconds ? `${avgDurationSeconds.toFixed(1)}s` : '—',
        delta: stats?.success_rate ? `${stats.success_rate}% success` : 'Throughput',
        description: 'Draft-to-complete runtime',
        sparkline: kpiSparklines,
      },
    ];
  }, [filteredHistory, stats, kpiSparklines]);

  const modelUsage = useMemo(() => {
    const totals = filteredHistory.reduce((acc, item) => {
      const model = normalizeModel(item.model_used);
      acc[model] = (acc[model] || 0) + 1;
      return acc;
    }, {});

    const totalCount = Object.values(totals).reduce((sum, count) => sum + count, 0) || 1;

    return Object.entries(totals)
      .map(([name, count]) => ({ name, percent: Math.round((count / totalCount) * 100) }))
      .sort((a, b) => b.percent - a.percent);
  }, [filteredHistory]);

  const coverageMatrix = useMemo(() => {
    if (!categorySummary.length) {
      return [
        { category: 'No content yet', pending: 0, running: 0, completed: 0, failed: 0 },
      ];
    }

    return categorySummary.map((row) => ({
      category: row.category,
      pending: row.pending,
      running: row.running,
      completed: row.completed,
      failed: row.failed,
    }));
  }, [categorySummary]);

  const upcomingSchedule = useMemo(() => {
    return filteredHistory
      .filter((item) => item.status !== 'failed')
      .sort((a, b) => new Date(b.created_at || b.started_at) - new Date(a.created_at || a.started_at))
      .slice(0, 6)
      .map((item) => ({
        day: new Date(item.created_at || item.started_at).toLocaleDateString(undefined, {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        }),
        title: item.topic,
        platform: normalizeType(item.content_type),
        status: item.status,
        category: normalizeType(item.content_type),
        model: normalizeModel(item.model_used),
      }));
  }, [filteredHistory]);

  const tasks = useMemo(() => {
    const actionables = filteredHistory
      .filter((item) => item.status === 'failed' || item.status === 'pending')
      .slice(0, 4)
      .map((item) => ({
        title: item.topic,
        due: formatRelative(item.created_at || item.started_at),
        assignee: normalizeType(item.content_type),
        status: item.status === 'failed' ? 'Needs review' : 'Queued',
      }));

    if (actionables.length === 0) {
      return [
        {
          title: 'No pending reviews',
          due: '—',
          assignee: 'All categories',
          status: 'Clear',
        },
      ];
    }

    return actionables;
  }, [filteredHistory]);

  const insights = useMemo(() => {
    if (!categorySummary.length) {
      return [
        {
          title: 'Add your first content',
          detail: 'Generate content to unlock coverage, model mix, and pipeline insights.',
          action: 'Start new piece',
        },
      ];
    }

    const weakest = [...categorySummary].sort((a, b) => a.completed - b.completed)[0];
    const strongest = [...categorySummary].sort((a, b) => b.completed - a.completed)[0];
    const topModel = modelUsage[0];

    return [
      {
        title: `Coverage gap: ${weakest.category}`,
        detail: `${weakest.completed} completed of ${weakest.total} generated. Add another to balance coverage.`,
        action: 'Plan content',
      },
      {
        title: `Lean into ${strongest.category}`,
        detail: `${strongest.completed} completed with ${Math.round(
          (strongest.completed / (strongest.total || 1)) * 100
        )}% completion rate. Repurpose into other channels.`,
        action: 'Repurpose piece',
      },
      topModel
        ? {
            title: 'Model mix',
            detail: `${topModel.name} produced ${topModel.percent}% of pieces. Diversify for style variety if needed.`,
            action: 'Adjust routing',
          }
        : null,
    ].filter(Boolean);
  }, [categorySummary, modelUsage]);

  return (
    <div className="dashboard-page">
      <header className="dashboard-hero">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>Content production overview</h1>
          <p className="subhead">
            Build, group, and ship generated content by category and model usage—grounded in stored pipeline runs.
          </p>
        </div>
        <div className="hero-actions">
          <button type="button" className="ghost">Import brief</button>
          <button type="button" className="primary">New content</button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="filter-bar" aria-label="Primary filters">
        <ChipFilterGroup
          label="Categories"
          options={categoryOptions}
          selected={selectedCategories}
          onChange={toggleCategory}
          multi
        />
        <ChipFilterGroup
          label="Status"
          options={statusOptions}
          selected={selectedStatus}
          onChange={setSelectedStatus}
        />
        <ChipFilterGroup
          label="Model used"
          options={modelOptions}
          selected={selectedModel}
          onChange={setSelectedModel}
        />
        <div className="filter-actions">
          <button type="button" className="ghost">Save segment</button>
        </div>
      </section>

      {loading ? (
        <div className="loading-state">Loading dashboard data...</div>
      ) : (
        <>
          <section className="kpi-grid" aria-label="Production KPIs">
            {primaryKpis.map((kpi) => (
              <article key={kpi.label} className="card kpi-card">
                <div className="kpi-header">
                  <p className="meta-label">{kpi.label}</p>
                  <span className="delta positive">{kpi.delta}</span>
                </div>
                <div className="kpi-value">{kpi.value}</div>
                <p className="muted">{kpi.description}</p>
                <Sparkline values={kpi.sparkline} />
              </article>
            ))}
          </section>

          <div className="dashboard-grid">
            <div className="primary-column">
              <section className="card band" aria-label="Category overview">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Content types</p>
                    <h3>Category-first overview</h3>
                  </div>
                  <button type="button" className="ghost">Sort by category</button>
                </header>
                <div className="campaign-row">
                  {categorySummary.map((category) => {
                    const readiness = Math.round((category.completed / (category.total || 1)) * 100);
                    const topModel = Object.entries(category.models).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';
                    const avgWords = category.words.length
                      ? Math.round(category.words.reduce((sum, w) => sum + w, 0) / category.words.length)
                      : '—';

                    return (
                      <article key={category.category} className="campaign-card">
                        <div className="campaign-top">
                          <h4>{category.category}</h4>
                          <span className="model-chip">{topModel}</span>
                        </div>
                        <div className="chip-row">
                          {category.topics.map((topic) => (
                            <span key={topic} className="chip pill">{topic}</span>
                          ))}
                        </div>
                        <div className="readiness">
                          <div className="readiness-bar">
                            <div style={{ width: `${readiness}%` }} />
                          </div>
                          <p className="muted">{readiness}% completed · {category.total} total</p>
                        </div>
                        <div className="campaign-meta">
                          <span className="meta-badge">Avg words {avgWords}</span>
                          <span className="meta-badge">Completed {category.completed}</span>
                          <span className="meta-badge">Queued {category.pending}</span>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>

              <section className="card" aria-label="Creation activity timeline">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Activity</p>
                    <h3>Production timeline</h3>
                  </div>
                  <div className="chip-row subtle">
                    <span className="chip pill light">Last 7 days</span>
                  </div>
                </header>
                <TimelineChart data={timelinePoints} />
              </section>

              <section className="card pipeline" aria-label="Pipeline snapshot">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Pipeline</p>
                    <h3>Snapshot by status</h3>
                  </div>
                  <button type="button" className="ghost">Open board</button>
                </header>
                <div className="lanes">
                  {['pending', 'running', 'completed', 'failed'].map((laneName) => (
                    <div key={laneName} className="lane">
                      <div className="lane-header">
                        <span className="lane-title">{statusLabels[laneName]}</span>
                        <span className="lane-count">{filteredHistory.filter((item) => item.status === laneName).length}</span>
                      </div>
                      <div className="lane-items">
                        {filteredHistory
                          .filter((item) => item.status === laneName)
                          .slice(0, 4)
                          .map((item) => (
                            <article key={`${laneName}-${item.pipeline_id}`} className="lane-card">
                              <div className="lane-card-top">
                                <span className="platform">{normalizeType(item.content_type)}</span>
                                <span className="model-chip subtle">{normalizeModel(item.model_used)}</span>
                              </div>
                              <h4>{item.topic}</h4>
                              <div className="chip-row">
                                <span className="chip pill">{statusLabels[item.status] || item.status}</span>
                                <span className="chip pill light">{formatRelative(item.created_at || item.started_at)}</span>
                              </div>
                            </article>
                          ))}
                        {filteredHistory.filter((item) => item.status === laneName).length === 0 && (
                          <p className="muted">No items in this lane.</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="card insights" aria-label="Insights and recommendations">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Insights</p>
                    <h3>Recommendations</h3>
                  </div>
                  <button type="button" className="ghost">View all</button>
                </header>
                <div className="insight-grid">
                  {insights.map((insight) => (
                    <article key={insight.title} className="insight-card">
                      <h4>{insight.title}</h4>
                      <p className="muted">{insight.detail}</p>
                      <button type="button" className="text-link">{insight.action}</button>
                    </article>
                  ))}
                </div>
              </section>
            </div>

            <div className="secondary-column">
              <section className="card" aria-label="Upcoming schedule">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Schedule</p>
                    <h3>Latest pieces</h3>
                  </div>
                  <button type="button" className="ghost">Open calendar</button>
                </header>
                <ul className="schedule-list">
                  {upcomingSchedule.length === 0 ? (
                    <li className="schedule-item">
                      <p className="muted">No items to show yet.</p>
                    </li>
                  ) : (
                    upcomingSchedule.map((item) => (
                      <li key={`${item.title}-${item.day}`} className="schedule-item">
                        <div>
                          <p className="meta-label">{item.day}</p>
                          <p className="item-title">{item.title}</p>
                          <div className="chip-row">
                            <span className="chip pill light">{item.platform}</span>
                            <span className="chip pill">{item.category}</span>
                            <span className="chip pill subtle">{item.model}</span>
                          </div>
                        </div>
                        <span className={`status-badge ${item.status}`}>{statusLabels[item.status] || item.status}</span>
                      </li>
                    ))
                  )}
                </ul>
              </section>

              <section className="card" aria-label="Tasks and approvals">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Tasks</p>
                    <h3>Approvals & reviews</h3>
                  </div>
                  <button type="button" className="ghost">Assign</button>
                </header>
                <ul className="task-list">
                  {tasks.map((task) => (
                    <li key={`${task.title}-${task.due}`} className="task-item">
                      <div>
                        <p className="item-title">{task.title}</p>
                        <p className="muted">Due {task.due} · {task.assignee}</p>
                      </div>
                      <span className="status-pill">{task.status}</span>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="card" aria-label="Model usage">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Model mix</p>
                    <h3>Generation sources</h3>
                  </div>
                  <button type="button" className="ghost">Edit routing</button>
                </header>
                <div className="model-usage">
                  {modelUsage.length === 0 ? (
                    <p className="muted">No model data available yet.</p>
                  ) : (
                    modelUsage.map((model) => (
                      <div key={model.name} className="model-row">
                        <div className="model-header">
                          <p className="item-title">{model.name}</p>
                          <p className="muted">{model.percent}%</p>
                        </div>
                        <div className="progress">
                          <div style={{ width: `${model.percent}%` }} />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </section>

              <section className="card" aria-label="Category coverage">
                <header className="section-header">
                  <div>
                    <p className="eyebrow">Coverage</p>
                    <h3>Category × status</h3>
                  </div>
                  <button type="button" className="ghost">Expand</button>
                </header>
                <div className="coverage-grid">
                  <div className="coverage-header">
                    <span>Category</span>
                    <span>Queued</span>
                    <span>Generating</span>
                    <span>Completed</span>
                    <span>Needs attention</span>
                  </div>
                  {coverageMatrix.map((row) => (
                    <div key={row.category} className="coverage-row">
                      <span>{row.category}</span>
                      <span>{row.pending}</span>
                      <span>{row.running}</span>
                      <span>{row.completed}</span>
                      <span>{row.failed}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DashboardPage;
