// PM2 ecosystem file - manages BOTH the FastAPI backend and the Next.js frontend.
// Ports are sourced from backend/.env (BACKEND_PORT) and frontend/.env (PORT) -
// nothing is hardcoded here. Edit those .env files to change ports; no need to
// touch this file or restart with different flags.

const fs = require("fs");
const path = require("path");

function loadEnvFile(filePath) {
  const result = {};
  if (!fs.existsSync(filePath)) return result;
  const content = fs.readFileSync(filePath, "utf-8");
  content.split("\n").forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return;
    const idx = trimmed.indexOf("=");
    if (idx === -1) return;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    result[key] = value;
  });
  return result;
}

const backendEnv = loadEnvFile(path.join(__dirname, "backend", ".env"));
const frontendEnv = loadEnvFile(path.join(__dirname, "frontend", ".env"));

const BACKEND_PORT = backendEnv.BACKEND_PORT || "8000";
const FRONTEND_PORT = frontendEnv.PORT || "3000";

module.exports = {
  apps: [
    {
      name: "pm2-dashboard-backend",
      cwd: "./backend",
      script: "venv/bin/uvicorn",
      args: `app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}`,
      interpreter: "none",
      env: { PYTHONUNBUFFERED: "1" },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },
    {
      name: "pm2-dashboard-frontend",
      cwd: "./frontend",
      script: "npm",
      args: "run start",
      env: { PORT: FRONTEND_PORT, NODE_ENV: "production" },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
    },
  ],
};
