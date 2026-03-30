import { FormEvent, MouseEvent as ReactMouseEvent, useEffect, useMemo, useState } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { api } from "./api";
import type { AccountInput, ChatMessage, DashboardResponse, EventItem, ObservabilitySummary, Recommendation, ResourceState } from "./types";

const emptyDashboard: DashboardResponse = {
  account: null,
  kpis: { monthly_cost: 0, projected_savings: 0, utilization_score: 0, alert_count: 0, services_covered: 0 },
  resources: [],
  recommendations: [],
  events: [],
  observability: { status: "healthy", metrics: [], recent_events: [] },
};

const accountDefaults: AccountInput = {
  student_name: "Mohan Achary",
  email: "student@example.edu",
  aws_account_id: "123456789012",
  connection_mode: "mocked",
  access_key_id: "AKIA-STUDENT-DEMO",
  secret_access_key: "demo-secret-placeholder",
  session_token: "",
  region: "ap-south-1",
  institution: "AWS Student Lab",
};

type ThemeMode = "light" | "dark";
type RecommendationAction = "accept" | "reject";

export default function App() {
  const [dashboard, setDashboard] = useState<DashboardResponse>(emptyDashboard);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "light";
    return (window.localStorage.getItem("cloud-optimizer-theme") as ThemeMode | null) ?? "light";
  });
  const [transitioningRecommendation, setTransitioningRecommendation] = useState<{ id: string; action: RecommendationAction } | null>(null);
  const [immersiveDashboard, setImmersiveDashboard] = useState(false);
  const [showChartLabels, setShowChartLabels] = useState(true);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("cloud-optimizer-theme", theme);
  }, [theme]);

  async function refreshAll() {
    setLoading(true);
    setError(null);
    try {
      const dashboardData = await api.getDashboard();
      setDashboard(dashboardData);
      try {
        setChatMessages(await api.getChatHistory());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  async function handleAccountCreate(payload: AccountInput) {
    setPosting(true);
    setError(null);
    try {
      await api.createAccount(payload);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPosting(false);
    }
  }

  async function handleRecommendation(id: string, action: RecommendationAction) {
    setPosting(true);
    setError(null);
    setTransitioningRecommendation({ id, action });
    try {
      await wait(260);
      if (action === "accept") {
        await api.acceptRecommendation(id);
      } else {
        await api.rejectRecommendation(id);
      }
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setTransitioningRecommendation(null);
      setPosting(false);
    }
  }

  async function handleRecurringRecommendation(id: string, action?: RecommendationAction) {
    setPosting(true);
    setError(null);
    try {
      const recurring = await api.recurRecommendation(id);
      if (action) {
        setTransitioningRecommendation({ id: recurring.id, action });
        await wait(220);
        if (action === "accept") {
          await api.acceptRecommendation(recurring.id);
        } else {
          await api.rejectRecommendation(recurring.id);
        }
      }
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setTransitioningRecommendation(null);
      setPosting(false);
    }
  }

  async function handleChat(message: string) {
    setPosting(true);
    setError(null);
    try {
      const response = await api.sendChatMessage(message);
      setChatMessages(response.history);
      setDashboard(await api.getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPosting(false);
    }
  }

  async function handleClearTimeline() {
    setPosting(true);
    setError(null);
    try {
      await api.clearEvents();
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPosting(false);
    }
  }

  async function handleClearChat() {
    setPosting(true);
    setError(null);
    try {
      await api.clearChatHistory();
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPosting(false);
    }
  }

  async function handleClearObservability() {
    setPosting(true);
    setError(null);
    try {
      await api.clearObservability();
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setPosting(false);
    }
  }

  const pageTitle =
    location.pathname === "/chat"
      ? "Chat"
      : location.pathname === "/account"
        ? "Account"
        : location.pathname === "/services"
          ? "Services"
          : "Dashboard";
  const pageIntro =
    location.pathname === "/chat"
      ? "Ask focused questions about recommendations, savings, and before-and-after impact."
      : location.pathname === "/account"
        ? "Switch between a clean mock setup and backend-validated real AWS credentials."
        : location.pathname === "/services"
          ? "A backend-fed services view for mocked and real account demonstrations, with each workload surfaced in a clearer operating layout."
        : "A minimal glass surface for costs, actions, and cloud guidance.";

  return (
    <div className={`site-shell theme-${theme}`}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <div className="ambient ambient-three" />

      <header className="site-header reveal reveal-1">
        <Link className="brand" to="/">
          <span className="brand-mark">C</span>
          <div>
            <span className="brand-name">Cloud Optimizer MCP</span>
            <span className="brand-subtitle mono-inline">mcp://cloud-optimizer/recommendations</span>
          </div>
        </Link>

        <nav className="site-nav">
          <NavLink to="/" label="Dashboard" active={location.pathname === "/"} />
          <NavLink to="/services" label="Services" active={location.pathname === "/services"} />
          <NavLink to="/chat" label="Chat" active={location.pathname === "/chat"} />
          <NavLink to="/account" label="Account" active={location.pathname === "/account"} />
        </nav>

        <div className="header-actions">
          <div className="header-status">
            <span className="status-dot" />
            <span>{dashboard.account ? `${dashboard.account.connection_mode} mode` : "not linked"}</span>
          </div>
          <button className="button button-subtle" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
            {theme === "light" ? "Dark mode" : "Light mode"}
          </button>
          <button className="button button-subtle" onClick={() => void refreshAll()} disabled={loading || posting}>
            Refresh
          </button>
        </div>
      </header>

      <main className="page-shell">
        <section className="hero reveal reveal-2">
          <div className="hero-copy">
            <span className="section-kicker animated-kicker">Cloud guidance</span>
            <h1 className="animated-title">{pageTitle}</h1>
            <p className="animated-copy">{pageIntro}</p>
          </div>

          <div className="hero-meta">
            <div className="meta-card">
              <span>Account</span>
              <strong>{dashboard.account ? dashboard.account.student_name : "Waiting for setup"}</strong>
              <small>{dashboard.account ? `${dashboard.account.connection_mode} AWS · ${dashboard.account.region}` : "Connect an account to unlock the experience"}</small>
            </div>
            <div className="meta-card">
              <span>Status</span>
              <strong>{loading ? "Loading" : "Ready"}</strong>
              <small className="mono-inline">sync://mcp-state/live-actions</small>
            </div>
          </div>
        </section>

        {error ? <div className="notice notice-error reveal reveal-3">Request error: {error}</div> : null}

        <div className="route-shell" key={location.pathname}>
          <Routes location={location}>
            <Route
              path="/"
              element={
                <DashboardPage
                  loading={loading}
                  data={dashboard}
                  onRecommendation={handleRecommendation}
                  onRecurringRecommendation={handleRecurringRecommendation}
                  busy={posting}
                  transitioningRecommendation={transitioningRecommendation}
                  immersiveDashboard={immersiveDashboard}
                  onToggleImmersive={() => setImmersiveDashboard((value) => !value)}
                  onClearTimeline={handleClearTimeline}
                  onClearObservability={handleClearObservability}
                  showChartLabels={showChartLabels}
                  onToggleChartLabels={() => setShowChartLabels((value) => !value)}
                />
              }
            />
            <Route
              path="/services"
              element={
                <ServicesPage
                  loading={loading}
                  data={dashboard}
                  onRecommendation={handleRecommendation}
                  onRecurringRecommendation={handleRecurringRecommendation}
                  busy={posting}
                  transitioningRecommendation={transitioningRecommendation}
                />
              }
            />
            <Route
              path="/chat"
              element={
                <ChatPage
                  messages={chatMessages}
                  onSend={handleChat}
                  recommendations={dashboard.recommendations}
                  busy={posting}
                  onRecommendation={handleRecommendation}
                  onRecurringRecommendation={handleRecurringRecommendation}
                  transitioningRecommendation={transitioningRecommendation}
                  onClearChat={handleClearChat}
                />
              }
            />
            <Route path="/account" element={<AccountPage accountDefaults={accountDefaults} existingAccount={dashboard.account} onSubmit={handleAccountCreate} busy={posting} />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

function NavLink({ to, label, active }: { to: string; label: string; active: boolean }) {
  return (
    <Link className={`nav-link ${active ? "active" : ""}`} to={to}>
      {label}
    </Link>
  );
}

function DashboardPage({
  loading,
  data,
  onRecommendation,
  onRecurringRecommendation,
  busy,
  transitioningRecommendation,
  immersiveDashboard,
  onToggleImmersive,
  onClearTimeline,
  onClearObservability,
  showChartLabels,
  onToggleChartLabels,
}: {
  loading: boolean;
  data: DashboardResponse;
  onRecommendation: (id: string, action: RecommendationAction) => Promise<void>;
  onRecurringRecommendation: (id: string, action?: RecommendationAction) => Promise<void>;
  busy: boolean;
  transitioningRecommendation: { id: string; action: RecommendationAction } | null;
  immersiveDashboard: boolean;
  onToggleImmersive: () => void;
  onClearTimeline: () => Promise<void>;
  onClearObservability: () => Promise<void>;
  showChartLabels: boolean;
  onToggleChartLabels: () => void;
}) {
  const openRecommendations = useMemo(
    () => data.recommendations.filter((item) => item.status === "open"),
    [data.recommendations],
  );
  const acceptedRecommendations = useMemo(
    () => data.recommendations.filter((item) => item.status === "accepted"),
    [data.recommendations],
  );
  const resolvedRecommendations = data.recommendations.length - openRecommendations.length;

  if (loading) {
    return <div className="surface reveal reveal-3">Loading dashboard...</div>;
  }

  if (!data.account) {
    return (
      <div className="empty-panel reveal reveal-3">
        <span className="section-kicker">Get started</span>
        <h2>Link an AWS account first</h2>
        <p>Once connected, Cloud Optimizer MCP seeds recommendations, metrics, and chat context so the experience feels complete immediately.</p>
        <Link className="button button-primary" to="/account">
          Open account setup
        </Link>
      </div>
    );
  }

  const account = data.account;

  return (
    <div className="page-grid">
      <section className="summary-row reveal reveal-3">
        <SummaryCard label="Monthly cost" value={`$${data.kpis.monthly_cost.toFixed(2)}`} detail="Current monthly estimate" />
        <SummaryCard label="Projected savings" value={`$${data.kpis.projected_savings.toFixed(2)}`} detail="Open recommendation upside" />
        <SummaryCard label="Utilization" value={`${data.kpis.utilization_score}%`} detail="Average across services" />
        <SummaryCard label="Alerts" value={String(data.kpis.alert_count)} detail="Remaining active signals" />
      </section>

      <section className="surface wide overview-surface reveal reveal-4">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Profile</span>
            <h2>{account.student_name}</h2>
          </div>
          <span className="badge">{account.connection_mode} AWS</span>
        </div>
        <p className="muted-text">
          {account.institution} in {account.region}. The dashboard is intentionally spare so changes feel immediate, clean, and readable in both themes.
        </p>
        <span className="mono-inline">account://{account.aws_account_id}</span>
      </section>

      <section className="surface wide reveal reveal-4">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Overview</span>
            <h2>Trends at a glance</h2>
          </div>
          <div className="surface-actions">
            <span className="muted-text mono-tertiary">Minimal motion, lightweight signals</span>
            <button className="button button-subtle button-compact" onClick={onToggleChartLabels}>
              {showChartLabels ? "Hide labels" : "Show labels"}
            </button>
            <button className="button button-subtle button-compact" onClick={onToggleImmersive}>
              {immersiveDashboard ? "Exit immersive" : "Immersive mode"}
            </button>
          </div>
        </div>
        <OverviewVisuals data={data} showLabels={showChartLabels} />
      </section>

      <section className="surface reveal reveal-5">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Inventory</span>
            <h2>Services</h2>
          </div>
          <span className="muted-text">{data.resources.length} tracked</span>
        </div>
        <div className="stack-list">
          {data.resources.map((resource) => (
            <article className="resource-row interactive-card" key={resource.id}>
              <div className="resource-main">
                <strong>{resource.name}</strong>
                <span>{resource.service} · {resource.region}</span>
              </div>
              <div className="resource-metrics">
                <span>${resource.monthly_cost.toFixed(2)}</span>
                <span>{resource.utilization}% util</span>
                <span>{resource.health_score} health</span>
                <span>{resource.alerts} alerts</span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="surface reveal reveal-6">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Recommendations</span>
            <h2>Queue</h2>
          </div>
          <span className="muted-text">{openRecommendations.length} open</span>
        </div>
        <div className="stack-list">
          {openRecommendations.length === 0 ? (
            <article className="mini-block">
              <strong>All suggestions resolved</strong>
              <span>Accepted or rejected items animate away from the queue as soon as you act on them.</span>
            </article>
          ) : (
            openRecommendations.map((recommendation) => (
              <RecommendationCard
                key={recommendation.id}
                item={recommendation}
                onAction={onRecommendation}
                busy={busy}
                transitionState={transitioningRecommendation?.id === recommendation.id ? transitioningRecommendation.action : null}
              />
            ))
          )}
        </div>
      </section>

      <section className="surface impact-surface reveal reveal-7">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Impact</span>
            <h2>Impact studio</h2>
          </div>
          <div className="surface-actions">
            <span className="muted-text mono-tertiary">{resolvedRecommendations} resolved</span>
            <span className="muted-text mono-tertiary">{acceptedRecommendations.length} accepted</span>
          </div>
        </div>
        <div className="impact-overview-grid">
          <article className="impact-stat-card interactive-card">
            <span className="section-kicker">Open upside</span>
            <strong>${data.kpis.projected_savings.toFixed(2)}</strong>
            <small>Potential monthly savings still available</small>
          </article>
          <article className="impact-stat-card interactive-card">
            <span className="section-kicker">Accepted wins</span>
            <strong>{acceptedRecommendations.length}</strong>
            <small>Recommendations already applied in the demo</small>
          </article>
          <article className="impact-stat-card interactive-card">
            <span className="section-kicker">Live choices</span>
            <strong>{openRecommendations.length}</strong>
            <small>Actions ready for yes or no decisions</small>
          </article>
        </div>
        <div className="compact-grid panel-scroll impact-scroll">
          {data.recommendations.map((item) => (
            <ImpactCard
              key={item.id}
              item={item}
              busy={busy}
              onRecommendation={onRecommendation}
              onRecurringRecommendation={onRecurringRecommendation}
              isMockMode={account.connection_mode === "mocked"}
              transitionState={transitioningRecommendation?.id === item.id ? transitioningRecommendation.action : null}
            />
          ))}
        </div>
      </section>

      <section className="surface timeline-surface reveal reveal-8">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Activity</span>
            <h2>Timeline</h2>
          </div>
          <button className="button button-subtle button-compact" onClick={() => void onClearTimeline()} disabled={busy || data.events.length === 0}>
            Clear
          </button>
        </div>
        <div className="panel-scroll timeline-scroll">
          <Timeline events={data.events} />
        </div>
      </section>

      <section className="surface wide observability-surface reveal reveal-9">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Observability</span>
            <h2>Operational signals</h2>
          </div>
          <div className="surface-actions">
            <span className="badge">{data.observability.status}</span>
            <button
              className="button button-subtle button-compact"
              onClick={() => void onClearObservability()}
              disabled={busy || (data.observability.metrics.length === 0 && data.observability.recent_events.length === 0)}
            >
              Clear
            </button>
          </div>
        </div>
        <ObservabilityPanel observability={data.observability} />
      </section>

      {immersiveDashboard ? <ImmersiveDashboard data={data} onClose={onToggleImmersive} showLabels={showChartLabels} onToggleChartLabels={onToggleChartLabels} /> : null}
    </div>
  );
}

function ChatPage({
  messages,
  onSend,
  recommendations,
  busy,
  onRecommendation,
  onRecurringRecommendation,
  transitioningRecommendation,
  onClearChat,
}: {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  recommendations: Recommendation[];
  busy: boolean;
  onRecommendation: (id: string, action: RecommendationAction) => Promise<void>;
  onRecurringRecommendation: (id: string, action?: RecommendationAction) => Promise<void>;
  transitioningRecommendation: { id: string; action: RecommendationAction } | null;
  onClearChat: () => Promise<void>;
}) {
  const [draft, setDraft] = useState("");
  const starters = [
    "Why is the top recommendation important?",
    "Compare before and after impact",
    "Summarize the accepted changes",
    "What is the next best action?",
  ];

  async function submit(message: string) {
    if (!message.trim()) return;
    await onSend(message);
    setDraft("");
  }

  return (
    <div className="page-grid chat-page">
      <section className="surface wide chat-main-surface reveal reveal-3">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Conversation</span>
            <h2>Optimization copilot</h2>
          </div>
          <div className="surface-actions">
            <span className="muted-text mono-tertiary">{messages.length} messages</span>
            <button className="button button-subtle button-compact" onClick={() => void onClearChat()} disabled={busy || messages.length === 0}>
              Clear
            </button>
          </div>
        </div>
        <div className="chat-stream panel-scroll chat-stream-scroll">
          {messages.length === 0 ? (
            <div className="empty-chat">Link an account first, then ask about recommendations, savings, and recent changes.</div>
          ) : (
            messages.map((message, index) => (
              <article className={`message reveal ${message.role}`} style={{ animationDelay: `${80 + index * 20}ms` }} key={message.id}>
                <span className="message-role">{message.role === "assistant" ? "Cloud Optimizer MCP" : "You"}</span>
                <p>{message.content}</p>
              </article>
            ))
          )}
        </div>
        <form
          className="composer"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            void submit(draft);
          }}
        >
          <textarea
            placeholder="Ask a focused question about costs, impact, or the next best action."
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={3}
          />
          <button className="button button-primary" disabled={busy}>
            Send
          </button>
        </form>
      </section>

      <section className="surface reveal reveal-4">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Suggestions</span>
            <h2>Prompts</h2>
          </div>
        </div>
        <div className="stack-list">
          {starters.map((starter) => (
            <button key={starter} className="button button-subtle align-left suggestion-button" onClick={() => void submit(starter)} disabled={busy}>
              {starter}
            </button>
          ))}
        </div>
      </section>

      <section className="surface chat-recommendation-surface reveal reveal-5">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Open items</span>
            <h2>Recommendations</h2>
          </div>
        </div>
        <div className="stack-list panel-scroll chat-recommendation-scroll">
          {recommendations.filter((item) => item.status === "open").map((item) => (
            <MiniRecommendationActionCard
              key={item.id}
              item={item}
              busy={busy}
              onRecommendation={onRecommendation}
              onRecurringRecommendation={onRecurringRecommendation}
              transitionState={transitioningRecommendation?.id === item.id ? transitioningRecommendation.action : null}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function ServicesPage({
  loading,
  data,
  onRecommendation,
  onRecurringRecommendation,
  busy,
  transitioningRecommendation,
}: {
  loading: boolean;
  data: DashboardResponse;
  onRecommendation: (id: string, action: RecommendationAction) => Promise<void>;
  onRecurringRecommendation: (id: string, action?: RecommendationAction) => Promise<void>;
  busy: boolean;
  transitioningRecommendation: { id: string; action: RecommendationAction } | null;
}) {
  if (loading) {
    return <div className="surface reveal reveal-3">Loading services...</div>;
  }

  if (!data.account) {
    return (
      <div className="empty-panel reveal reveal-3">
        <span className="section-kicker">Backend feed</span>
        <h2>Connect an account to load services</h2>
        <p>This tab shows the service inventory coming from the backend, including mocked workloads for demos.</p>
        <Link className="button button-primary" to="/account">
          Open account setup
        </Link>
      </div>
    );
  }

  const groupedResources = data.resources.reduce<Record<ResourceState["service"], ResourceState[]>>(
    (groups, resource) => {
      groups[resource.service].push(resource);
      return groups;
    },
    { EC2: [], RDS: [], S3: [], Lambda: [] },
  );

  return (
    <div className="page-grid services-page">
      <section className="surface wide reveal reveal-3">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Backend services</span>
            <h2>{data.account.connection_mode === "mocked" ? "Mocked service fabric" : "Connected service fabric"}</h2>
          </div>
          <span className="badge">{data.resources.length} workloads</span>
        </div>
        <div className="service-hero-grid">
          <article className="service-hero-card interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
            <span className="mono-inline">backend://resource-feed/live</span>
            <strong>Mixed compute, storage, database, and functions from the backend</strong>
            <p>
              This view is separate from the dashboard so you can demo the raw service layer, especially in mocked AWS mode where recurring actions matter.
            </p>
          </article>
          <article className="service-hero-card interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
            <span className="mono-inline">mode://{data.account.connection_mode}</span>
            <strong>{data.account.connection_mode === "mocked" ? "Recurring demo-ready services" : "Validated account-backed services"}</strong>
            <p>Each card below is built from backend resource state and linked recommendations, not hardcoded frontend content.</p>
          </article>
        </div>
      </section>

      {Object.entries(groupedResources).map(([service, resources], index) => (
        <section className="surface wide reveal services-cluster" style={{ animationDelay: `${160 + index * 50}ms` }} key={service}>
          <div className="surface-header">
            <div>
              <span className="section-kicker">Service cluster</span>
              <h2>{service}</h2>
            </div>
            <span className="mono-inline">cluster://{service.toLowerCase()}/{resources.length}</span>
          </div>

          {resources.length === 0 ? (
            <article className="mini-block interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
              <strong>No {service} workloads</strong>
              <span>The backend did not return any items for this service class.</span>
            </article>
          ) : (
            <div className="service-cluster-grid panel-scroll service-cluster-scroll">
              {resources.map((resource) => {
                const related = data.recommendations.filter((item) => item.target_resource_id === resource.id);

                return (
                  <article className="service-resource-card interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave} key={resource.id}>
                    <div className="service-resource-head">
                      <div>
                        <span className="mono-inline">resource://{resource.id}</span>
                        <h3>{resource.name}</h3>
                      </div>
                      <span className="badge">{resource.region}</span>
                    </div>

                    <div className="service-metric-strip">
                      <div>
                        <span>Cost</span>
                        <strong>${resource.monthly_cost.toFixed(2)}</strong>
                      </div>
                      <div>
                        <span>Util</span>
                        <strong>{resource.utilization}%</strong>
                      </div>
                      <div>
                        <span>Health</span>
                        <strong>{resource.health_score}</strong>
                      </div>
                      <div>
                        <span>Alerts</span>
                        <strong>{resource.alerts}</strong>
                      </div>
                    </div>

                    <div className="stack-list">
                      {related.length === 0 ? (
                        <div className="mini-block service-inline-note">
                          <strong>No linked recommendation</strong>
                          <span>This workload is currently stable in the backend recommendation engine.</span>
                        </div>
                      ) : (
                        related.map((item) => (
                          <ImpactCard
                            key={item.id}
                            item={item}
                            busy={busy}
                            onRecommendation={onRecommendation}
                            onRecurringRecommendation={onRecurringRecommendation}
                            isMockMode={data.account?.connection_mode === "mocked"}
                            transitionState={transitioningRecommendation?.id === item.id ? transitioningRecommendation.action : null}
                          />
                        ))
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}

function AccountPage({
  accountDefaults,
  existingAccount,
  onSubmit,
  busy,
}: {
  accountDefaults: AccountInput;
  existingAccount: DashboardResponse["account"];
  onSubmit: (payload: AccountInput) => Promise<void>;
  busy: boolean;
}) {
  const [form, setForm] = useState<AccountInput>(accountDefaults);
  const isRealMode = form.connection_mode === "real";

  return (
    <div className="page-grid account-page">
      <section className="surface wide reveal reveal-3">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Account</span>
            <h2>Connect AWS</h2>
          </div>
          <span className="badge">{isRealMode ? "real validation" : "mock mode"}</span>
        </div>

        <form
          className="account-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onSubmit(form);
          }}
        >
          <div className="field-row field-row-tight">
            <label className="field">
              <span>Connection mode</span>
              <select value={form.connection_mode} onChange={(event) => setForm({ ...form, connection_mode: event.target.value as "mocked" | "real" })}>
                <option value="mocked">Mocked demo AWS</option>
                <option value="real">Real AWS via backend validation</option>
              </select>
            </label>
          </div>

          <div className="field-row">
            <label className="field">
              <span>Student name</span>
              <input value={form.student_name} onChange={(event) => setForm({ ...form, student_name: event.target.value })} />
            </label>
            <label className="field">
              <span>Email</span>
              <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            </label>
          </div>

          <div className="field-row">
            <label className="field">
              <span>AWS account ID</span>
              <input value={form.aws_account_id} onChange={(event) => setForm({ ...form, aws_account_id: event.target.value })} />
            </label>
            <label className="field">
              <span>Region</span>
              <input value={form.region} onChange={(event) => setForm({ ...form, region: event.target.value })} />
            </label>
          </div>

          <div className="field-row">
            <label className="field">
              <span>Institution</span>
              <input value={form.institution} onChange={(event) => setForm({ ...form, institution: event.target.value })} />
            </label>
          </div>

          <div className="field-row">
            <label className="field">
              <span>AWS access key ID</span>
              <input placeholder={placeholderForField("access_key_id", isRealMode)} value={form.access_key_id} onChange={(event) => setForm({ ...form, access_key_id: event.target.value })} />
            </label>
            <label className="field">
              <span>AWS secret access key</span>
              <input type="password" placeholder={placeholderForField("secret_access_key", isRealMode)} value={form.secret_access_key} onChange={(event) => setForm({ ...form, secret_access_key: event.target.value })} />
            </label>
          </div>

          <div className="field-row">
            <label className="field">
              <span>Session token</span>
              <input type="password" placeholder={placeholderForField("session_token", isRealMode)} value={form.session_token} onChange={(event) => setForm({ ...form, session_token: event.target.value })} />
            </label>
          </div>

          <div className="notice">
            {isRealMode
              ? "Real mode validates credentials through the backend and then keeps the experience grounded in the demo dataset."
              : "Mock mode skips AWS validation and instantly seeds the product with sample cloud usage."}
          </div>

          <div className="action-row">
            <button className="button button-primary" disabled={busy}>
              {existingAccount ? `Refresh ${form.connection_mode} account` : `Link ${form.connection_mode} account`}
            </button>
          </div>
        </form>
      </section>

      <section className="surface reveal reveal-4">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Flow</span>
            <h2>What happens next</h2>
          </div>
        </div>
        <div className="stack-list">
          <article className="mini-block interactive-card">
            <strong>Mock mode</strong>
            <span>Seeds account, recommendations, events, and chat instantly.</span>
          </article>
          <article className="mini-block interactive-card">
            <strong>Real mode</strong>
            <span>Validates AWS credentials in the backend before opening the same product flow.</span>
          </article>
          <article className="mini-block interactive-card">
            <strong>Telemetry</strong>
            <span>Datadog-style counters and events continue to update either way.</span>
          </article>
        </div>
      </section>

      {existingAccount ? (
        <section className="surface reveal reveal-5">
          <div className="surface-header">
            <div>
              <span className="section-kicker">Current</span>
              <h2>Linked account</h2>
            </div>
          </div>
          <div className="stack-list">
            <article className="mini-block interactive-card">
              <strong>{existingAccount.student_name}</strong>
              <span>{existingAccount.email}</span>
            </article>
            <article className="mini-block interactive-card">
              <strong>{existingAccount.connection_mode} AWS</strong>
              <span>{existingAccount.region}</span>
            </article>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function SummaryCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="summary-card interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function OverviewVisuals({ data, showLabels }: { data: DashboardResponse; showLabels: boolean }) {
  const { costSeries, pieSegments } = getOverviewData(data);

  return (
    <div className="overview-layout">
      <article className="chart-card chart-panel interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
        <div className="chart-header">
          <strong>Cost trend</strong>
          <span className="mono-inline">trend://last-6-syncs</span>
        </div>
        <LineTrendChart values={costSeries} showLabels={showLabels} />
      </article>

      <article className="chart-card chart-panel interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
        <div className="chart-header">
          <strong>Service mix</strong>
          <span className="mono-inline">pie://monthly-cost-share</span>
        </div>
        <PieMixChart segments={pieSegments} showLabels={showLabels} />
      </article>
    </div>
  );
}

function ImmersiveDashboard({
  data,
  onClose,
  showLabels,
  onToggleChartLabels,
}: {
  data: DashboardResponse;
  onClose: () => void;
  showLabels: boolean;
  onToggleChartLabels: () => void;
}) {
  const { costSeries, pieSegments } = getOverviewData(data);

  return (
    <div className="immersive-overlay" onClick={onClose}>
      <div className="immersive-panel" onClick={(event) => event.stopPropagation()}>
        <div className="immersive-header">
          <div>
            <span className="section-kicker">Immersive mode</span>
            <h2>Analytics canvas</h2>
            <span className="mono-inline">mcp://immersive/overview</span>
          </div>
          <div className="surface-actions">
            <button className="button button-subtle button-compact" onClick={onToggleChartLabels}>
              {showLabels ? "Hide labels" : "Show labels"}
            </button>
            <button className="button button-subtle button-compact" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
        <div className="immersive-body">
          <section className="immersive-hero interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
            <div>
              <span className="section-kicker">MCP cloud field</span>
              <h3>Live optimization canvas</h3>
              <p>
                A full-frame analytics mode for demos, with cost drift, service share, and lightweight operational text arranged like a control surface.
              </p>
            </div>
            <div className="immersive-notes">
              <span className="mono-inline">mcp://graphs/cost-wave</span>
              <span className="mono-inline">mcp://graphs/service-split</span>
              <span className="mono-inline">sync://live-dashboard/frame</span>
            </div>
          </section>

          <div className="immersive-grid">
            <article className="chart-card immersive-chart immersive-wide interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
              <div className="chart-header">
                <strong>Cost orbit</strong>
                <span className="mono-inline">trend://immersive-cost-field</span>
              </div>
              <LineTrendChart values={costSeries} showLabels={showLabels} />
              <div className="immersive-caption">
                <span>Projected savings: ${data.kpis.projected_savings.toFixed(2)}</span>
                <span>Alerts in frame: {data.kpis.alert_count}</span>
              </div>
            </article>

            <article className="chart-card immersive-chart interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
              <div className="chart-header">
                <strong>Service split</strong>
                <span className="mono-inline">pie://immersive-mix</span>
              </div>
              <PieMixChart segments={pieSegments} showLabels={showLabels} />
            </article>

            <article className="immersive-metrics interactive-card tilt-card" onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
              <div className="immersive-metric">
                <span className="section-kicker">Cost layer</span>
                <strong>${data.kpis.monthly_cost.toFixed(2)}</strong>
                <small>Current monthly estimate</small>
              </div>
              <div className="immersive-metric">
                <span className="section-kicker">Efficiency layer</span>
                <strong>{data.kpis.utilization_score}%</strong>
                <small>Utilization across tracked services</small>
              </div>
              <div className="immersive-metric">
                <span className="section-kicker">Action layer</span>
                <strong>{data.recommendations.filter((item) => item.status === "open").length}</strong>
                <small>Open recommendations on screen</small>
              </div>
              <div className="immersive-metric">
                <span className="section-kicker">MCP pulse</span>
                <strong>{data.observability.status}</strong>
                <small>Operational state mirror</small>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  );
}

function LineTrendChart({ values, showLabels }: { values: number[]; showLabels: boolean }) {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = Math.max(max - min, 1);
  const chartPoints = values.map((value, index) => {
    const x = 10 + (index * 80) / Math.max(values.length - 1, 1);
    const y = 84 - ((value - min) / range) * 58;
    return { x, y, value, label: `T${index + 1}` };
  });
  const points = buildSmoothPath(chartPoints);

  return (
    <div className="chart-frame">
      <div className={`chart-meta-row ${showLabels ? "" : "is-hidden"}`}>
        <span>Low ${min.toFixed(0)}</span>
        <span>High ${max.toFixed(0)}</span>
      </div>
      <svg className="line-chart" viewBox="0 0 100 100" aria-hidden="true">
        <path d="M10 84 H90" className="chart-axis" />
        <path d="M10 54 H90" className="chart-axis chart-axis-soft" />
        <path d={points} className="chart-line-shadow" />
        <path d={points} className="chart-line" />
        {chartPoints.map((point, index) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="1.7" className="chart-point" />
            {showLabels && (index === 0 || index === chartPoints.length - 1 || index === Math.floor(chartPoints.length / 2)) ? (
              <text x={point.x} y={point.y - 5} textAnchor="middle" className="chart-point-label">
                ${point.value.toFixed(0)}
              </text>
            ) : null}
          </g>
        ))}
      </svg>
      <div className={`chart-x-labels ${showLabels ? "" : "is-hidden"}`} aria-hidden="true">
        {chartPoints.map((point) => (
          <span key={point.label}>{point.label}</span>
        ))}
      </div>
    </div>
  );
}

function PieMixChart({ segments, showLabels }: { segments: Array<{ label: string; value: number; ratio: number }>; showLabels: boolean }) {
  let cumulative = 0;
  const colors = ["var(--chart-accent)", "var(--chart-soft)", "var(--chart-muted)", "var(--chart-warm)"];
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);

  if (segments.length === 0) {
    return <div className="chart-empty mono-tertiary">No service mix available</div>;
  }

  return (
    <div className="pie-layout">
      <svg className="pie-chart" viewBox="0 0 120 120" aria-hidden="true">
        <circle cx="60" cy="60" r="40" fill="none" stroke="var(--accent-soft)" strokeWidth="12" />
        {segments.map((segment, index) => {
          const dash = segment.ratio * 251.2;
          const offset = -cumulative * 251.2;
          cumulative += segment.ratio;
          return (
            <circle
              key={segment.label}
              cx="60"
              cy="60"
              r="40"
              fill="none"
              stroke={colors[index % colors.length]}
              strokeWidth="12"
              strokeDasharray={`${dash} 251.2`}
              strokeDashoffset={offset}
              transform="rotate(-90 60 60)"
              className="pie-segment"
            />
          );
        })}
        <circle cx="60" cy="60" r="26" fill="var(--surface-strong)" />
        <text x="60" y="56" textAnchor="middle" className="pie-center-value">
          ${total.toFixed(0)}
        </text>
        <text x="60" y="68" textAnchor="middle" className="pie-center-label">
          total
        </text>
      </svg>
      <div className={`pie-legend ${showLabels ? "" : "is-hidden"}`}>
        {segments.map((segment) => (
          <div className="legend-row" key={segment.label}>
            <strong>{segment.label}</strong>
            <span>
              ${segment.value.toFixed(0)} · {Math.round(segment.ratio * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecommendationCard({
  item,
  onAction,
  busy,
  transitionState,
}: {
  item: Recommendation;
  onAction: (id: string, action: RecommendationAction) => Promise<void>;
  busy: boolean;
  transitionState: RecommendationAction | null;
}) {
  const transitionClass = transitionState ? `is-leaving ${transitionState}` : "";

  return (
    <article
      className={`recommendation-card interactive-card tilt-card ${transitionClass}`}
      onMouseMove={handleTiltMove}
      onMouseLeave={handleTiltLeave}
    >
      <div className="recommendation-top">
        <span className="severity-tag">{item.severity}</span>
        <span className="badge">{item.status}</span>
      </div>
      <h3>{item.title}</h3>
      <p>{item.rationale}</p>
      <div className="recommendation-meta">
        <span>Save ${item.projected_savings.toFixed(2)}</span>
        <span>{item.service}</span>
      </div>
      <div className="action-row">
        <button className="button button-primary" disabled={busy} onClick={() => void onAction(item.id, "accept")}>
          Accept
        </button>
        <button className="button button-subtle" disabled={busy} onClick={() => void onAction(item.id, "reject")}>
          Reject
        </button>
      </div>
    </article>
  );
}

function ImpactCard({
  item,
  busy,
  onRecommendation,
  onRecurringRecommendation,
  isMockMode,
  transitionState,
}: {
  item: Recommendation;
  busy: boolean;
  onRecommendation: (id: string, action: RecommendationAction) => Promise<void>;
  onRecurringRecommendation: (id: string, action?: RecommendationAction) => Promise<void>;
  isMockMode: boolean;
  transitionState: RecommendationAction | null;
}) {
  const actionable = item.status === "open";
  const transitionClass = transitionState ? `is-leaving ${transitionState}` : "";

  return (
    <article className={`impact-card interactive-card tilt-card ${transitionClass}`} onMouseMove={handleTiltMove} onMouseLeave={handleTiltLeave}>
      <div className="impact-topline">
        <span className="mono-tag">{item.service}</span>
        <span className="badge">{item.status}</span>
      </div>
      <strong>{item.title}</strong>
      <p>{item.impact.summary}</p>
      <div className="impact-values">
        <span>{signedCurrency(item.impact.monthly_cost_delta)}</span>
        <span>{signedValue(item.impact.utilization_delta, "% util")}</span>
        <span>{signedValue(item.impact.health_score_delta, " health")}</span>
      </div>
      {actionable ? (
        <div className="mini-actions">
          <button className="button button-primary button-compact" disabled={busy} onClick={() => void onRecommendation(item.id, "accept")}>
            Accept
          </button>
          <button className="button button-subtle button-compact" disabled={busy} onClick={() => void onRecommendation(item.id, "reject")}>
            Reject
          </button>
        </div>
      ) : (
        <div className="mini-actions">
          <span className="mono-inline mono-tertiary">state://{item.status}</span>
          {isMockMode ? (
            <>
              <button className="button button-subtle button-compact" disabled={busy} onClick={() => void onRecurringRecommendation(item.id)}>
                Replay
              </button>
              <button className="button button-primary button-compact" disabled={busy} onClick={() => void onRecurringRecommendation(item.id, "accept")}>
                Yes
              </button>
              <button className="button button-subtle button-compact" disabled={busy} onClick={() => void onRecurringRecommendation(item.id, "reject")}>
                No
              </button>
            </>
          ) : null}
        </div>
      )}
    </article>
  );
}

function MiniRecommendationActionCard({
  item,
  busy,
  onRecommendation,
  onRecurringRecommendation,
  transitionState,
}: {
  item: Recommendation;
  busy: boolean;
  onRecommendation: (id: string, action: RecommendationAction) => Promise<void>;
  onRecurringRecommendation: (id: string, action?: RecommendationAction) => Promise<void>;
  transitionState: RecommendationAction | null;
}) {
  const transitionClass = transitionState ? `is-leaving ${transitionState}` : "";

  return (
    <article
      className={`mini-block interactive-card tilt-card mini-recommendation ${transitionClass}`}
      onMouseMove={handleTiltMove}
      onMouseLeave={handleTiltLeave}
    >
      <strong>{item.title}</strong>
      <span>{item.status} · save ${item.projected_savings.toFixed(2)}</span>
      <div className="mini-actions">
        <button className="button button-primary button-compact" disabled={busy} onClick={() => void onRecommendation(item.id, "accept")}>
          Yes
        </button>
        <button className="button button-subtle button-compact" disabled={busy} onClick={() => void onRecommendation(item.id, "reject")}>
          No
        </button>
        <button className="button button-subtle button-compact" disabled={busy} onClick={() => void onRecurringRecommendation(item.id)}>
          Replay
        </button>
      </div>
    </article>
  );
}

function Timeline({ events }: { events: EventItem[] }) {
  return (
    <div className="timeline">
      {events.map((event, index) => (
        <article
          className="timeline-item interactive-card tilt-card"
          style={{ animationDelay: `${80 + index * 30}ms` }}
          onMouseMove={handleTiltMove}
          onMouseLeave={handleTiltLeave}
          key={event.id}
        >
          <strong>{event.title}</strong>
          <p>{event.description}</p>
          <small>{new Date(event.created_at).toLocaleString()}</small>
        </article>
      ))}
    </div>
  );
}

function ObservabilityPanel({ observability }: { observability: ObservabilitySummary }) {
  return (
    <div className="observability-board">
      <section className="observability-hero interactive-card">
        <span className="section-kicker">Status</span>
        <h3>{observability.status}</h3>
        <p>Datadog-style request counters, backend metrics, and recent operational events in one compact monitoring surface.</p>
      </section>

      <div className="observability-metric-grid">
        {observability.metrics.length === 0 ? (
          <article className="mini-block interactive-card">
            <strong>No metrics yet</strong>
            <span>They will appear as the dashboard and chat are used.</span>
          </article>
        ) : (
          observability.metrics.map((metric) => (
            <article className="metric-tile interactive-card" key={metric.name}>
              <span className="section-kicker">{metric.name}</span>
              <strong>{metric.value}</strong>
              <small>{new Date(metric.last_updated).toLocaleTimeString()}</small>
            </article>
          ))
        )}
      </div>

      <aside className="observability-events-panel">
        <div className="surface-header">
          <div>
            <span className="section-kicker">Recent signals</span>
            <h3>Events feed</h3>
          </div>
          <span className="mono-inline">ops://recent-events/{observability.recent_events.length}</span>
        </div>
        <div className="panel-scroll observability-events-scroll">
          <Timeline events={observability.recent_events} />
        </div>
      </aside>
    </div>
  );
}

function placeholderForField(field: string, isRealMode: boolean) {
  if (!isRealMode) {
    if (field === "access_key_id") return "AKIA-STUDENT-DEMO";
    if (field === "secret_access_key") return "demo-secret-placeholder";
    if (field === "session_token") return "Optional for mock mode";
  }
  if (field === "access_key_id") return "Enter real AWS access key ID";
  if (field === "secret_access_key") return "Enter real AWS secret access key";
  if (field === "session_token") return "Enter AWS session token if required";
  return "";
}

function getOverviewData(data: DashboardResponse) {
  const costSeries = [
    Math.max(data.kpis.monthly_cost + 18, 20),
    Math.max(data.kpis.monthly_cost + 8, 20),
    Math.max(data.kpis.monthly_cost + 12, 20),
    Math.max(data.kpis.monthly_cost - 4, 20),
    Math.max(data.kpis.monthly_cost - 9, 20),
    Math.max(data.kpis.monthly_cost, 20),
  ];
  const totalCost = Math.max(data.resources.reduce((sum, item) => sum + item.monthly_cost, 0), 1);
  const pieSegments = data.resources.map((item) => ({
    label: item.service,
    value: item.monthly_cost,
    ratio: item.monthly_cost / totalCost,
  }));

  return { costSeries, pieSegments };
}

function handleTiltMove(event: ReactMouseEvent<HTMLElement>) {
  const target = event.currentTarget;
  if (target.dataset.hoverReady === "true") return;
  target.dataset.hoverReady = "true";
}

function handleTiltLeave(event: ReactMouseEvent<HTMLElement>) {
  const target = event.currentTarget;
  target.dataset.hoverReady = "false";
}

function buildSmoothPath(points: Array<{ x: number; y: number }>) {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

  let path = `M ${points[0].x} ${points[0].y}`;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];
    const controlX = (previous.x + current.x) / 2;
    path += ` C ${controlX} ${previous.y}, ${controlX} ${current.y}, ${current.x} ${current.y}`;
  }
  return path;
}

function signedCurrency(value: number) {
  return `${value >= 0 ? "+" : ""}$${value.toFixed(2)}`;
}

function signedValue(value: number, suffix: string) {
  return `${value >= 0 ? "+" : ""}${value}${suffix}`;
}

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
