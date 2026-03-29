export type RecommendationStatus = "open" | "accepted" | "rejected";

export interface AccountProfile {
  id: string;
  student_name: string;
  email: string;
  aws_account_id: string;
  connection_mode: "mocked" | "real";
  region: string;
  institution: string;
  connected: boolean;
  access_key_id_last4?: string | null;
  validated_arn?: string | null;
  validated_user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResourceState {
  id: string;
  service: "EC2" | "RDS" | "S3" | "Lambda";
  name: string;
  region: string;
  monthly_cost: number;
  utilization: number;
  health_score: number;
  alerts: number;
  status: string;
}

export interface ImpactPreview {
  monthly_cost_delta: number;
  utilization_delta: number;
  health_score_delta: number;
  alerts_delta: number;
  summary: string;
}

export interface Recommendation {
  id: string;
  title: string;
  service: ResourceState["service"];
  severity: "low" | "medium" | "high";
  rationale: string;
  projected_savings: number;
  status: RecommendationStatus;
  target_resource_id: string;
  impact: ImpactPreview;
}

export interface EventItem {
  id: string;
  type: string;
  title: string;
  description: string;
  created_at: string;
}

export interface TelemetryMetric {
  name: string;
  value: number;
  last_updated: string;
}

export interface ObservabilitySummary {
  status: string;
  metrics: TelemetryMetric[];
  recent_events: EventItem[];
}

export interface DashboardKpis {
  monthly_cost: number;
  projected_savings: number;
  utilization_score: number;
  alert_count: number;
  services_covered: number;
}

export interface DashboardResponse {
  account: AccountProfile | null;
  kpis: DashboardKpis;
  resources: ResourceState[];
  recommendations: Recommendation[];
  events: EventItem[];
  observability: ObservabilitySummary;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  recommendation_id?: string | null;
  resource_id?: string | null;
}

export interface ChatResponse {
  reply: ChatMessage;
  history: ChatMessage[];
}

export interface AccountInput {
  student_name: string;
  email: string;
  aws_account_id: string;
  connection_mode: "mocked" | "real";
  access_key_id: string;
  secret_access_key: string;
  session_token: string;
  region: string;
  institution: string;
}
