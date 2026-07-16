import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_admin
from app.ssl_models import SSLServer, SSLCertificate
from app.ssl_schemas import SSLServerCreate, SSLServerOut
from app.ssl_manager import discover_and_check, renew_certificate, SSLCheckError

router = APIRouter(prefix="/ssl", tags=["ssl"])


def _cert_status(cert: SSLCertificate, threshold_days: int) -> str:
    if cert.last_check_error:
        return "unknown"
    if cert.days_remaining is None:
        return "unknown"
    if cert.days_remaining < 0:
        return "expired"
    if cert.days_remaining <= threshold_days:
        return "critical"
    if cert.days_remaining <= threshold_days * 2:
        return "warning"
    return "ok"


def _server_to_out(server: SSLServer) -> SSLServerOut:
    from app.ssl_schemas import SSLCertificateOut

    certs_out = [
        SSLCertificateOut(
            id=c.id,
            domain_name=c.domain_name,
            config_file=c.config_file,
            cert_path=c.cert_path,
            expiry_date=c.expiry_date,
            days_remaining=c.days_remaining,
            last_checked_at=c.last_checked_at,
            last_check_error=c.last_check_error,
            status=_cert_status(c, server.threshold_days),
        )
        for c in server.certificates
    ]
    return SSLServerOut(
        id=server.id,
        name=server.name,
        ip_address=server.ip_address,
        conf_dir=server.conf_dir,
        threshold_days=server.threshold_days,
        certificates=certs_out,
    )


@router.get("/servers", response_model=list[SSLServerOut])
def list_ssl_servers(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return [_server_to_out(s) for s in db.query(SSLServer).all()]


@router.post("/servers", response_model=SSLServerOut)
def create_ssl_server(payload: SSLServerCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    server = SSLServer(**payload.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    return _server_to_out(server)


@router.delete("/servers/{server_id}")
def delete_ssl_server(server_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    server = db.query(SSLServer).filter(SSLServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(server)
    db.commit()
    return {"detail": "deleted"}


@router.post("/servers/{server_id}/check", response_model=SSLServerOut)
def check_ssl_server(server_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    server = db.query(SSLServer).filter(SSLServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Not found")

    now = datetime.datetime.utcnow()
    try:
        results = discover_and_check(server)
    except SSLCheckError as exc:
        for cert in server.certificates:
            cert.last_check_error = str(exc)
            cert.last_checked_at = now
        if not server.certificates:
            db.add(SSLCertificate(server_id=server.id, last_check_error=str(exc), last_checked_at=now))
        db.commit()
        db.refresh(server)
        return _server_to_out(server)

    existing = {(c.config_file, c.domain_name): c for c in server.certificates}
    seen_keys = set()

    for r in results:
        key = (r["config_file"], r["domain_name"])
        seen_keys.add(key)
        cert = existing.get(key)
        if not cert:
            cert = SSLCertificate(server_id=server.id, config_file=r["config_file"], domain_name=r["domain_name"])
            db.add(cert)
        cert.cert_path = r["cert_path"]
        cert.expiry_date = r["expiry_date"]
        cert.days_remaining = r["days_remaining"]
        cert.last_check_error = r["error"]
        cert.last_checked_at = now

    # जो certs पहले मिले थे पर अब config में नहीं हैं (file हटी/domain हटा), उन्हें हटा देते हैं
    for key, cert in existing.items():
        if key not in seen_keys:
            db.delete(cert)

    db.commit()
    db.refresh(server)
    return _server_to_out(server)


@router.post("/certificates/{cert_id}/renew")
def renew_ssl_certificate(cert_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    cert = db.query(SSLCertificate).filter(SSLCertificate.id == cert_id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Not found")
    if not cert.cert_path:
        raise HTTPException(status_code=400, detail="No certificate path recorded yet - run Check now first.")

    try:
        result = renew_certificate(cert.server, cert.cert_path)
    except SSLCheckError as exc:
        cert.last_check_error = str(exc)
        cert.last_checked_at = datetime.datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc))

    cert.expiry_date = result["expiry_date"]
    cert.days_remaining = result["days_remaining"]
    cert.last_check_error = None
    cert.last_checked_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(cert)
    return {"detail": result["message"], "days_remaining": cert.days_remaining, "expiry_date": cert.expiry_date}
