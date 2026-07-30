import shlex
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app import models, schemas
from app.ssh_manager import run_command as ssh_run_command, _connect as ssh_connect, SSHConnectionError

router = APIRouter(prefix="/servers/{server_id}/logs", tags=["server-logs"])


@router.get("/sources", response_model=List[schemas.LogSourceOut])
def list_log_sources(server_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.ServerLogSource).filter_by(server_id=server_id).all()


@router.post("/sources", response_model=schemas.LogSourceOut)
def add_log_source(
    server_id: int,
    payload: schemas.LogSourceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    server = db.query(models.Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "Server not found")

    source = models.ServerLogSource(
        server_id=server_id,
        label=payload.label,
        remote_path=payload.remote_path,
        created_by=getattr(user, "id", None),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}")
def delete_log_source(server_id: int, source_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    source = db.query(models.ServerLogSource).filter_by(id=source_id, server_id=server_id).first()
    if not source:
        raise HTTPException(404, "Log source not found")
    db.delete(source)
    db.commit()
    return {"ok": True}


def _get_source_or_404(db: Session, server_id: int, source_id: int) -> models.ServerLogSource:
    source = db.query(models.ServerLogSource).filter_by(id=source_id, server_id=server_id).first()
    if not source:
        raise HTTPException(404, "Log source not found")
    return source


def _get_server_or_404(db: Session, server_id: int) -> models.Server:
    server = db.query(models.Server).filter_by(id=server_id).first()
    if not server:
        raise HTTPException(404, "Server not found")
    return server


def _parse_ls_line(line: str) -> Optional[schemas.LogFileEntry]:
    parts = line.split(maxsplit=8)
    if len(parts) < 9:
        return None
    perms, _links, _owner, _group, size, date, time_, _tz, name = parts
    if perms.startswith("d"):
        return None
    try:
        size_bytes = int(size)
    except ValueError:
        return None
    modified = f"{date}T{time_.split('.')[0]}"
    return schemas.LogFileEntry(
        name=name,
        size_bytes=size_bytes,
        modified=modified,
        is_gz=name.endswith(".gz"),
    )


@router.get("/sources/{source_id}/files", response_model=List[schemas.LogFileEntry])
def list_log_files(server_id: int, source_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    server = _get_server_or_404(db, server_id)
    source = _get_source_or_404(db, server_id, source_id)

    safe_path = shlex.quote(source.remote_path)
    try:
        out = ssh_run_command(server, f"ls -la --time-style=full-iso {safe_path}", timeout=20)
    except SSHConnectionError as exc:
        raise HTTPException(502, f"Could not list directory: {exc}")

    cutoff = datetime.now() - timedelta(days=3)
    entries = []
    for line in out.splitlines():
        parsed = _parse_ls_line(line)
        if not parsed:
            continue
        if parsed.modified:
            try:
                if datetime.fromisoformat(parsed.modified) < cutoff:
                    continue
            except ValueError:
                pass
        entries.append(parsed)

    entries.sort(key=lambda e: e.modified or "", reverse=True)
    return entries


@router.get("/sources/{source_id}/files/{filename}/tail", response_model=schemas.LogTailResponse)
def tail_log_file(
    server_id: int,
    source_id: int,
    filename: str,
    lines: int = 200,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    server = _get_server_or_404(db, server_id)
    source = _get_source_or_404(db, server_id, source_id)

    lines = max(1, min(lines, 2000))
    full_path = shlex.quote(f"{source.remote_path.rstrip('/')}/{filename}")

    if filename.endswith(".gz"):
        cmd = f"zcat {full_path} | tail -n {lines}"
    else:
        cmd = f"tail -n {lines} {full_path}"

    try:
        out = ssh_run_command(server, cmd, timeout=30)
    except SSHConnectionError as exc:
        raise HTTPException(502, f"Could not read file: {exc}")

    result_lines = out.splitlines()
    return schemas.LogTailResponse(
        filename=filename,
        lines=result_lines,
        truncated=len(result_lines) >= lines,
    )


@router.get("/sources/{source_id}/files/{filename}/download")
def download_log_file(
    server_id: int,
    source_id: int,
    filename: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    server = _get_server_or_404(db, server_id)
    source = _get_source_or_404(db, server_id, source_id)

    full_path = f"{source.remote_path.rstrip('/')}/{filename}"

    try:
        client = ssh_connect(server)
    except SSHConnectionError as exc:
        raise HTTPException(502, f"Could not connect: {exc}")

    sftp = client.open_sftp()

    try:
        remote_file = sftp.open(full_path, "rb")
        remote_file.set_pipelined(True)
    except FileNotFoundError:
        sftp.close()
        client.close()
        raise HTTPException(404, "File not found on remote server")

    def stream_chunks(chunk_size: int = 1024 * 256):
        try:
            while True:
                chunk = remote_file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            remote_file.close()
            sftp.close()
            client.close()

    media_type = "application/gzip" if filename.endswith(".gz") else "text/plain"
    return StreamingResponse(
        stream_chunks(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
