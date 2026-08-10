import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
});

// Attach the JWT (stored in localStorage after login) to every request.
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("pm2dash_token");
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Redirect to /login on 401s - but NOT for the login request itself, otherwise
// a wrong password just hard-reloads the page instead of showing the error.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLoginRequest = err?.config?.url?.includes("/auth/login");
    if (typeof window !== "undefined" && err?.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem("pm2dash_token");
      localStorage.removeItem("pm2dash_role");
      localStorage.removeItem("pm2dash_username");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// ---- Types ----
export type Role = "admin" | "developer" | "viewer";

export interface ClientItem {
  id: number;
  name: string;
  description?: string | null;
  server_count: number;
  created_at: string;
}

export interface ServerItem {
  id: number;
  client_id: number;
  name: string;
  ip_address: string;
  ssh_port: number;
  ssh_username: string;
  pm2_path?: string | null;
  environment: "Dev" | "Prod" | "Stg" | "Other";
  tag?: string | null;
  online?: boolean | null;
}

export interface PM2ProcessItem {
  pm_id: number;
  name: string;
  pid?: number | null;
  status: string;
  cpu?: number | null;
  memory?: number | null;
  uptime?: number | null;
  restarts?: number | null;
  instances?: number | null;
  exec_mode?: string | null;
  cwd?: string | null;
}

export interface UserItem {
  id: number;
  username: string;
  email?: string | null;
  role: Role;
  is_active: boolean;
}

export interface RepoItem {
  name: string;
}

export interface EnvKeyItem {
  key: string;
  is_sensitive: boolean;
  value?: string | null;
}

export interface EnvFileItem {
  file_path: string;
  keys: EnvKeyItem[];
}

// ---- Server Resources (CPU/RAM/Disk) ----
export interface ServerResourceItem {
  server_id: number;
  name: string;
  status: "online" | "offline" | "error";
  cpu_percent?: number | null;
  ram_used_mb?: number | null;
  ram_total_mb?: number | null;
  ram_percent?: number | null;
  disk_used?: string | null;
  disk_total?: string | null;
  disk_percent?: number | null;
  error?: string | null;
}

export interface ClientResourceItem {
  client_id: number;
  client_name: string;
  servers: ServerResourceItem[];
}

export async function fetchAllResources(): Promise<ClientResourceItem[]> {
  const res = await api.get("/server-resources");
  return res.data;
}

export async function fetchClientResources(clientId: number): Promise<ClientResourceItem> {
  const res = await api.get(`/server-resources/clients/${clientId}`);
  return res.data;
}

// ---- Docker Containers ----
export interface DockerContainerItem {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  ports?: string;
  created?: string;
}

// ---- Kubernetes ----
export type K8sConnectionType = "ssh_kubectl" | "kubeconfig" | "api_token";

export interface K8sClusterItem {
  id: number;
  client_id: number;
  name: string;
  environment?: string | null;
  connection_type: K8sConnectionType;
  online?: boolean | null;
}

export interface K8sPodItem {
  name: string;
  namespace: string;
  phase: string;
  node_name?: string | null;
  restarts: number;
  created: string;
}


export interface K8sClientItem {
  id: number;
  name: string;
  description?: string | null;
  cluster_count: number;
  created_at: string;
}

// ---- InfraLink Agents (Phase 1: registration, heartbeat, status) ----
export interface InfraLinkAgentItem {
  id: string;
  server_id: number;
  status: "online" | "offline";
  hostname?: string | null;
  os?: string | null;
  agent_version?: string | null;
  cpu_percent?: number | null;
  ram_percent?: number | null;
  disk_percent?: number | null;
  last_seen_at?: string | null;
}

export interface InfraLinkRegistrationTokenItem {
  token: string;
  expires_at: string;
}

export async function fetchInfraLinkAgents(): Promise<InfraLinkAgentItem[]> {
  const res = await api.get("/api/infralink/agents");
  return res.data;
}

export async function createInfraLinkRegistrationToken(
  serverId: number,
  ttlMinutes: number = 15
): Promise<InfraLinkRegistrationTokenItem> {
  const res = await api.post("/api/infralink/registration-tokens", {
    server_id: serverId,
    ttl_minutes: ttlMinutes,
  });
  return res.data;
}
