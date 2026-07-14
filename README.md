# PM2 Dashboard

Centralized dashboard to monitor and control PM2 processes across many
client servers, over SSH, from one place.

```
Cards UI (Next.js) → Client → Server → PM2 Processes → Live Logs (WebSocket)
        ↓
FastAPI backend (Paramiko/SSH) → remote servers running PM2
        ↓
MySQL (clients, servers, users, audit log)
```

## Stack

- **Backend:** Python, FastAPI, Paramiko (SSH), SQLAlchemy, JWT auth
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Database:** MySQL (tables: `users`, `clients`, `servers`, `process_log_audit`)
- **Process management / deployment:** PM2 (`ecosystem.config.js` runs both backend + frontend)
- **Config:** everything via `.env` files — nothing hardcoded

## Features

- Role-based permissions:
  - **Admin** — add/remove clients & servers, control processes, manage users
  - **Developer** — view processes & stream live logs, restart/stop/start processes
  - **Viewer** — read-only: browse clients/servers/processes and view logs
- Dynamic environment detection per server (`Dev` / `Prod` / `Stg`, otherwise `Other`)
  based on the server name/tag/IP; can also be set explicitly when adding a server
- Real-time PM2 log streaming over WebSocket (`pm2 logs <name> --raw`)
- Admin UI to add a new client (name) and new server (name + IP + SSH creds) directly from the dashboard

## Repository layout

```
pm2-dashboard/
├── backend/                # FastAPI app
│   ├── app/
│   │   ├── main.py         # app entrypoint
│   │   ├── config.py       # loads all settings from .env
│   │   ├── database.py     # SQLAlchemy engine/session
│   │   ├── models.py       # users, clients, servers, audit log
│   │   ├── schemas.py      # pydantic request/response models
│   │   ├── auth.py         # JWT + role-based dependencies
│   │   ├── ssh_manager.py  # Paramiko: pm2 jlist / actions / log streaming
│   │   ├── init_db.py      # creates tables + seeds default admin
│   │   └── routers/        # auth, clients, servers, processes, logs (ws)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Next.js app
│   ├── app/                 # login, dashboard, [clientId], [serverId], logs
│   ├── components/          # cards, modals, live log terminal
│   ├── lib/                 # api client + auth context
│   ├── package.json
│   └── .env.local.example
├── ecosystem.config.js      # PM2 config managing backend + frontend
├── docker-compose.yml       # optional local MySQL for dev
└── README.md
```

## 1. Database setup

Either run MySQL yourself, or use the bundled compose file for local dev:

```bash
docker compose up -d mysql
```

## 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DB_HOST/DB_USER/DB_PASSWORD/DB_NAME, SECRET_KEY, DEFAULT_ADMIN_* etc.

python -m app.init_db           # creates tables + default admin user
uvicorn app.main:app --reload --port 8000   # dev server
```

The default admin credentials come from `DEFAULT_ADMIN_USERNAME` /
`DEFAULT_ADMIN_PASSWORD` in `.env`. **Log in and rotate this password
immediately** in a real deployment (use `POST /auth/users` to create
additional accounts with the desired role).

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
# edit .env.local: point NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL at your backend

npm run dev      # dev server on :3000
```

## 4. Production deployment with PM2

From the repo root, after building the frontend and creating the backend venv:

```bash
cd frontend && npm run build && cd ..
pm2 start ecosystem.config.js
pm2 save
pm2 status
```

This runs both `pm2-dashboard-backend` (uvicorn on :8000) and
`pm2-dashboard-frontend` (Next.js on :3000) under PM2 — the same PM2
that the dashboard itself will be monitoring on your remote client servers.

## 5. Connecting client servers

Log in as admin → **Add Client** → open the client → **Add Server**
(name, IP, SSH port/user, and either a password or a private-key path
that exists on the *backend* host). The backend SSHes into that server
on demand to run `pm2 jlist` / `pm2 restart|stop|start <name>` and to
stream `pm2 logs <name> --raw` over the WebSocket endpoint.

Each server's environment badge (`Dev`/`Prod`/`Stg`/`Other`) is either
set explicitly in the Add Server form, or auto-detected from the
server's name/tag/IP if left on "Auto-detect".

## API overview

| Method | Endpoint                                          | Access                  |
|--------|----------------------------------------------------|--------------------------|
| POST   | `/auth/login`                                      | public                   |
| GET    | `/auth/me`                                          | any authenticated user   |
| POST   | `/auth/users`                                       | admin                    |
| GET    | `/clients`                                          | any authenticated user   |
| POST   | `/clients`                                          | admin                    |
| GET    | `/servers?client_id=`                               | any authenticated user   |
| POST   | `/servers`                                          | admin                    |
| GET    | `/servers/{id}/processes`                           | any authenticated user   |
| POST   | `/servers/{id}/processes/{name}/action`             | admin, developer         |
| WS     | `/ws/logs/{server_id}/{process_name}?token=<jwt>`   | any authenticated user   |

## Notes / production hardening ideas

- SSH credentials are currently stored as plain columns for simplicity — encrypt
  `ssh_password` at rest (e.g. via a KMS-backed field) before going to production.
- Add HTTPS/WSS termination (nginx/Caddy) in front of both PM2-managed processes.
- Consider connection pooling/caching for `pm2 jlist` if you have many servers,
  since each dashboard refresh opens a fresh SSH session per server.
