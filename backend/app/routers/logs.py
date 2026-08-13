import asyncio
import queue
import threading
import time
from types import SimpleNamespace

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.auth import get_user_from_token_str
from app.models import Server, ProcessLogAudit
from app.ssh_manager import stream_logs, stream_docker_logs, SSHConnectionError
from app.k8s_models import K8sCluster
from app.k8s_manager import stream_pod_logs, K8sConnectionError

router = APIRouter(tags=["logs"])


def _snapshot_server(server: Server) -> SimpleNamespace:
    """Copies the fields stream_logs()/_connect() need into a plain object
    not bound to any SQLAlchemy session, to avoid DetachedInstanceError
    once the request's db session is closed."""
    return SimpleNamespace(
        id=server.id,
        ip_address=server.ip_address,
        ssh_port=server.ssh_port,
        ssh_username=server.ssh_username,
        ssh_password=server.ssh_password,
        ssh_private_key_path=server.ssh_private_key_path,
        pm2_path=getattr(server, "pm2_path", None),
    )


def _producer_thread(server: Server, process_name: str, q: "queue.Queue", stop_event: threading.Event):
    try:
        for line in stream_logs(server, process_name):
            if stop_event.is_set():
                break
            if line is None:
                time.sleep(0.2)
                continue
            q.put(line)
    except SSHConnectionError as exc:
        q.put(f"__ERROR__:{exc}")
    except Exception as exc:  # noqa: BLE001 - surface unexpected errors instead of silently closing
        q.put(f"__ERROR__:Unexpected error: {exc}")
    finally:
        q.put(None)  # sentinel: stream ended


@router.websocket("/ws/logs/{server_id}/{process_name}")
async def websocket_logs(websocket: WebSocket, server_id: int, process_name: str, token: str = Query(...)):
    await websocket.accept()

    db: Session = SessionLocal()
    try:
        user = get_user_from_token_str(token, db)
        if not user:
            await websocket.send_text("__ERROR__: Invalid or expired token")
            await websocket.close(code=4401)
            return

        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            await websocket.send_text("__ERROR__: Server not found")
            await websocket.close(code=4404)
            return

        # audit trail
        db.add(ProcessLogAudit(server_id=server_id, process_name=process_name, user_id=user.id))
        db.commit()
        server_snapshot = _snapshot_server(server)
    finally:
        db.close()

    log_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_producer_thread, args=(server_snapshot, process_name, log_queue, stop_event), daemon=True
    )
    thread.start()

    try:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, log_queue.get, True, 1.0)
            except queue.Empty:
                # send a ping to detect client disconnects promptly
                await websocket.send_text("__PING__")
                continue

            if line is None:
                await websocket.send_text("__STREAM_CLOSED__")
                break
            await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()


def _producer_thread_docker(server: Server, container_name: str, q: "queue.Queue", stop_event: threading.Event):
    try:
        for line in stream_docker_logs(server, container_name):
            if stop_event.is_set():
                break
            if line is None:
                time.sleep(0.2)
                continue
            q.put(line)
    except SSHConnectionError as exc:
        q.put(f"__ERROR__:{exc}")
    except Exception as exc:  # noqa: BLE001
        q.put(f"__ERROR__:Unexpected error: {exc}")
    finally:
        q.put(None)


@router.websocket("/ws/docker-logs/{server_id}/{container_name}")
async def websocket_docker_logs(websocket: WebSocket, server_id: int, container_name: str, token: str = Query(...)):
    await websocket.accept()
    db: Session = SessionLocal()
    try:
        user = get_user_from_token_str(token, db)
        if not user:
            await websocket.send_text("__ERROR__: Invalid or expired token")
            await websocket.close(code=4401)
            return
        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            await websocket.send_text("__ERROR__: Server not found")
            await websocket.close(code=4404)
            return
        db.add(ProcessLogAudit(server_id=server_id, process_name=f"docker:{container_name}", user_id=user.id))
        db.commit()
        server_snapshot = _snapshot_server(server)
    finally:
        db.close()

    log_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_producer_thread_docker, args=(server_snapshot, container_name, log_queue, stop_event), daemon=True
    )
    thread.start()
    try:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, log_queue.get, True, 1.0)
            except queue.Empty:
                await websocket.send_text("__PING__")
                continue
            if line is None:
                await websocket.send_text("__STREAM_CLOSED__")
                break
            await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()


def _producer_thread_k8s(cluster: K8sCluster, namespace: str, pod_name: str, q: "queue.Queue", stop_event: threading.Event):
    try:
        for line in stream_pod_logs(cluster, namespace, pod_name):
            if stop_event.is_set():
                break
            if line is None:
                time.sleep(0.2)
                continue
            q.put(line)
    except K8sConnectionError as exc:
        q.put(f"__ERROR__:{exc}")
    except Exception as exc:  # noqa: BLE001
        q.put(f"__ERROR__:Unexpected error: {exc}")
    finally:
        q.put(None)


@router.websocket("/ws/k8s-logs/{cluster_id}/{namespace}/{pod_name}")
async def websocket_k8s_logs(websocket: WebSocket, cluster_id: int, namespace: str, pod_name: str, token: str = Query(...)):
    await websocket.accept()
    db: Session = SessionLocal()
    try:
        user = get_user_from_token_str(token, db)
        if not user:
            await websocket.send_text("__ERROR__: Invalid or expired token")
            await websocket.close(code=4401)
            return
        cluster = db.query(K8sCluster).filter(K8sCluster.id == cluster_id).first()
        if not cluster:
            await websocket.send_text("__ERROR__: Cluster not found")
            await websocket.close(code=4404)
            return
        # ProcessLogAudit.server_id is a FK into `servers`, and K8s clusters
        # have no row there (server_id=0 doesn't exist) - this insert always
        # violates the FK constraint. Audit logging must never block the
        # actual log stream, so any failure here is caught and rolled back;
        # it only means this one view isn't recorded in the audit trail.
        try:
            db.add(ProcessLogAudit(server_id=0, process_name=f"k8s:{cluster.name}:{namespace}/{pod_name}", user_id=user.id))
            db.commit()
        except Exception:
            db.rollback()
        db.refresh(cluster)
        db.expunge(cluster)
    finally:
        db.close()

    log_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_producer_thread_k8s, args=(cluster, namespace, pod_name, log_queue, stop_event), daemon=True
    )
    thread.start()
    try:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, log_queue.get, True, 1.0)
            except queue.Empty:
                await websocket.send_text("__PING__")
                continue
            if line is None:
                await websocket.send_text("__STREAM_CLOSED__")
                break
            await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
