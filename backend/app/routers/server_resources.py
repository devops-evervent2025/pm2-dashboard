from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models import Server, Client, User
from app.ssh_manager import run_command, SSHConnectionError
from app.server_resource_models import ServerResourceLog

router = APIRouter(prefix="/server-resources", tags=["server-resources"])

STATS_CMD = (
    "echo '__CPU__'; top -bn1 | grep 'Cpu(s)' | awk '{print $2+$4}'; "
    "echo '__MEM__'; free -m | awk 'NR==2{print $3, $2}'; "
    "echo '__DISK__'; df -h / | awk 'NR==2{print $3, $2, $4, $5, $6}'"
)


class ServerResourceOut(BaseModel):
    server_id: int
    name: str
    status: str
    ip_address: str | None = None
    cpu_percent: float | None = None
    ram_used_mb: int | None = None
    ram_total_mb: int | None = None
    ram_percent: float | None = None
    disk_used: str | None = None
    disk_total: str | None = None
    disk_free: str | None = None
    disk_percent: float | None = None
    mount_point: str | None = None
    error: str | None = None


class ClientResourceOut(BaseModel):
    client_id: int
    client_name: str
    servers: list[ServerResourceOut]


def _parse_stats(raw: str) -> dict:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    result = {}

    try:
        i = lines.index("__CPU__")
        result["cpu_percent"] = round(float(lines[i + 1]), 1)
    except (ValueError, IndexError):
        result["cpu_percent"] = None

    try:
        i = lines.index("__MEM__")
        used, total = lines[i + 1].split()
        used, total = int(used), int(total)
        result["ram_used_mb"] = used
        result["ram_total_mb"] = total
        result["ram_percent"] = round(used * 100 / total, 1) if total else None
    except (ValueError, IndexError):
        result["ram_used_mb"] = result["ram_total_mb"] = result["ram_percent"] = None

    try:
        i = lines.index("__DISK__")
        parts = lines[i + 1].split()
        used, total, avail, pct = parts[0], parts[1], parts[2], parts[3]
        mount = parts[4] if len(parts) > 4 else "/"
        result["disk_used"] = used
        result["disk_total"] = total
        result["disk_free"] = avail
        result["disk_percent"] = float(pct.strip("%"))
        result["mount_point"] = mount
    except (ValueError, IndexError):
        result["disk_used"] = result["disk_total"] = result["disk_percent"] = None
        result["disk_free"] = result["mount_point"] = None

    return result


def _fetch_one(server: Server) -> ServerResourceOut:
    try:
        raw = run_command(server, STATS_CMD, timeout=10)
        stats = _parse_stats(raw)
        return ServerResourceOut(
            server_id=server.id, name=server.name, status="online",
            ip_address=server.ip_address, **stats
        )
    except SSHConnectionError as exc:
        return ServerResourceOut(
            server_id=server.id, name=server.name, status="offline",
            ip_address=server.ip_address, error=str(exc)
        )
    except Exception as exc:
        return ServerResourceOut(
            server_id=server.id, name=server.name, status="error",
            ip_address=server.ip_address, error=str(exc)
        )


def _collect(servers: list[Server]) -> list[ServerResourceOut]:
    if not servers:
        return []
    results: list[ServerResourceOut] = []
    with ThreadPoolExecutor(max_workers=min(len(servers), 8)) as executor:
        futures = {executor.submit(_fetch_one, s): s for s in servers}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda r: r.server_id)
    return results


def _log_results(db: Session, client_id: int, results: list[ServerResourceOut]) -> None:
    for r in results:
        db.add(ServerResourceLog(
            server_id=r.server_id,
            client_id=client_id,
            cpu_percent=r.cpu_percent,
            ram_used_mb=r.ram_used_mb,
            ram_total_mb=r.ram_total_mb,
            ram_percent=r.ram_percent,
            disk_used=r.disk_used,
            disk_total=r.disk_total,
            disk_percent=r.disk_percent,
            status=r.status,
            error_message=r.error,
        ))
    db.commit()


@router.get("/clients/{client_id}", response_model=ClientResourceOut)
def get_client_resources(client_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    servers = db.query(Server).filter(Server.client_id == client_id).all()
    results = _collect(servers)
    _log_results(db, client_id, results)
    return ClientResourceOut(client_id=client.id, client_name=client.name, servers=results)


@router.get("", response_model=list[ClientResourceOut])
def get_all_clients_resources(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    clients = db.query(Client).all()
    output = []
    for client in clients:
        servers = db.query(Server).filter(Server.client_id == client.id).all()
        results = _collect(servers)
        _log_results(db, client.id, results)
        output.append(ClientResourceOut(client_id=client.id, client_name=client.name, servers=results))
    return output
