"""
Talks to a Kubernetes cluster using whichever connection_type it's
configured with. Every public function here takes a K8sCluster row and
returns plain dicts/strings - callers (the router) never need to know
which underlying method was used.
"""
import json
import shlex
from typing import List, Optional, Generator

import paramiko
from kubernetes import client as k8s_client
from kubernetes.client import Configuration as K8sConfiguration
import yaml
import tempfile
import os

from app.k8s_models import K8sCluster, K8sConnectionTypeEnum
from app.config import get_settings

settings = get_settings()


class K8sConnectionError(Exception):
    pass


# ---------------- ssh_kubectl backend ----------------

def _ssh_connect(cluster: K8sCluster) -> paramiko.SSHClient:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = dict(
        hostname=cluster.ssh_ip_address,
        port=cluster.ssh_port or 22,
        username=cluster.ssh_username or "root",
        timeout=settings.SSH_CONNECT_TIMEOUT,
        banner_timeout=settings.SSH_CONNECT_TIMEOUT,
        auth_timeout=settings.SSH_CONNECT_TIMEOUT,
    )
    if cluster.ssh_password:
        connect_kwargs["password"] = cluster.ssh_password
    elif cluster.ssh_private_key_path:
        connect_kwargs["key_filename"] = cluster.ssh_private_key_path
    try:
        c.connect(**connect_kwargs)
    except Exception as exc:
        raise K8sConnectionError(f"SSH connect failed to {cluster.ssh_ip_address}: {exc}") from exc
    return c


def _kubectl_bin(cluster: K8sCluster) -> str:
    return shlex.quote(cluster.kubectl_path) if cluster.kubectl_path else "kubectl"


def _ssh_run(cluster: K8sCluster, command: str, timeout: int = 20) -> str:
    c = _ssh_connect(cluster)
    try:
        wrapped = f"bash -lc {shlex.quote(command)}"
        stdin, stdout, stderr = c.exec_command(wrapped, timeout=timeout)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        if not out and err:
            raise K8sConnectionError(err.strip())
        return out
    finally:
        c.close()


def _ssh_list_pods(cluster: K8sCluster) -> List[dict]:
    raw = _ssh_run(cluster, f"{_kubectl_bin(cluster)} get pods -A -o json")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise K8sConnectionError(f"Could not parse kubectl output: {exc}") from exc
    return [_normalize_pod(item) for item in data.get("items", [])]


def _ssh_pod_action(cluster: K8sCluster, namespace: str, pod_name: str, action: str) -> str:
    ns = shlex.quote(namespace)
    name = shlex.quote(pod_name)
    if action == "delete":
        return _ssh_run(cluster, f"{_kubectl_bin(cluster)} delete pod {name} -n {ns}")
    raise K8sConnectionError(f"Unsupported action for ssh_kubectl: {action}")


def _ssh_stream_logs(cluster: K8sCluster, namespace: str, pod_name: str) -> Generator[Optional[str], None, None]:
    c = _ssh_connect(cluster)
    try:
        transport = c.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        cmd = f"{_kubectl_bin(cluster)} logs -f --tail=100 {shlex.quote(pod_name)} -n {shlex.quote(namespace)}"
        channel.exec_command(f"bash -lc {shlex.quote(cmd)}")
        buffer = b""
        while True:
            if channel.recv_ready():
                chunk = channel.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    yield line.decode(errors="ignore")
            elif channel.exit_status_ready():
                break
            else:
                yield None
    finally:
        try:
            channel.close()
        except Exception:
            pass
        c.close()


# ---------------- kubeconfig / api_token backend (direct API, shared code) ----------------

def _build_api_client(cluster: K8sCluster) -> k8s_client.ApiClient:
    if cluster.connection_type == K8sConnectionTypeEnum.kubeconfig:
        if not cluster.kubeconfig_yaml:
            raise K8sConnectionError("This cluster has no kubeconfig stored.")
        # kubernetes-client only loads kubeconfig from a file path, so we
        # write it to a private temp file scoped to this one call.
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(cluster.kubeconfig_yaml)
            temp_path = f.name
        try:
            from kubernetes import config as k8s_config
            api_client = k8s_config.new_client_from_config(config_file=temp_path)
        except Exception as exc:
            raise K8sConnectionError(f"Invalid kubeconfig: {exc}") from exc
        finally:
            os.unlink(temp_path)
        return api_client

    if cluster.connection_type == K8sConnectionTypeEnum.api_token:
        if not cluster.api_server_url or not cluster.api_token:
            raise K8sConnectionError("This cluster is missing its API server URL or token.")
        conf = K8sConfiguration()
        conf.host = cluster.api_server_url
        conf.api_key = {"authorization": f"Bearer {cluster.api_token}"}
        conf.verify_ssl = (cluster.api_verify_ssl != "no")
        if cluster.api_ca_cert:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False) as f:
                f.write(cluster.api_ca_cert)
                conf.ssl_ca_cert = f.name
        return k8s_client.ApiClient(configuration=conf)

    raise K8sConnectionError(f"Unsupported connection_type for direct API: {cluster.connection_type}")


def _normalize_pod(item: dict) -> dict:
    """Accepts either a raw kubectl JSON item (dict) or a kubernetes-client
    V1Pod.to_dict() item, and returns the same flat shape either way."""
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    spec = item.get("spec", {})
    container_statuses = status.get("containerStatuses") or status.get("container_statuses") or []
    restarts = sum(cs.get("restartCount", cs.get("restart_count", 0)) or 0 for cs in container_statuses)
    return {
        "name": metadata.get("name"),
        "namespace": metadata.get("namespace"),
        "phase": status.get("phase", "Unknown"),
        "node_name": spec.get("nodeName", spec.get("node_name")),
        "restarts": restarts,
        "created": metadata.get("creationTimestamp", metadata.get("creation_timestamp")) or "",
    }


def _api_list_pods(cluster: K8sCluster) -> List[dict]:
    api_client = _build_api_client(cluster)
    try:
        v1 = k8s_client.CoreV1Api(api_client)
        pods = v1.list_pod_for_all_namespaces(watch=False)
        return [_normalize_pod(p.to_dict()) for p in pods.items]
    except Exception as exc:
        raise K8sConnectionError(f"Kubernetes API error: {exc}") from exc


def _api_pod_action(cluster: K8sCluster, namespace: str, pod_name: str, action: str) -> str:
    api_client = _build_api_client(cluster)
    v1 = k8s_client.CoreV1Api(api_client)
    try:
        if action == "delete":
            v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            return f"Pod {pod_name} deleted."
        raise K8sConnectionError(f"Unsupported action: {action}")
    except K8sConnectionError:
        raise
    except Exception as exc:
        raise K8sConnectionError(f"Kubernetes API error: {exc}") from exc


def _api_stream_logs(cluster: K8sCluster, namespace: str, pod_name: str) -> Generator[Optional[str], None, None]:
    api_client = _build_api_client(cluster)
    v1 = k8s_client.CoreV1Api(api_client)
    try:
        resp = v1.read_namespaced_pod_log(
            name=pod_name, namespace=namespace, follow=True,
            tail_lines=100, _preload_content=False,
        )
        for raw_line in resp:
            line = raw_line.decode(errors="ignore") if isinstance(raw_line, bytes) else str(raw_line)
            for sub_line in line.splitlines():
                yield sub_line
    except Exception as exc:
        yield f"__ERROR__:Kubernetes API error: {exc}"


# ---------------- public interface - dispatches on connection_type ----------------

def list_pods(cluster: K8sCluster) -> List[dict]:
    if cluster.connection_type == K8sConnectionTypeEnum.ssh_kubectl:
        return _ssh_list_pods(cluster)
    return _api_list_pods(cluster)


def pod_action(cluster: K8sCluster, namespace: str, pod_name: str, action: str) -> str:
    if cluster.connection_type == K8sConnectionTypeEnum.ssh_kubectl:
        return _ssh_pod_action(cluster, namespace, pod_name, action)
    return _api_pod_action(cluster, namespace, pod_name, action)


def stream_pod_logs(cluster: K8sCluster, namespace: str, pod_name: str) -> Generator[Optional[str], None, None]:
    if cluster.connection_type == K8sConnectionTypeEnum.ssh_kubectl:
        yield from _ssh_stream_logs(cluster, namespace, pod_name)
    else:
        yield from _api_stream_logs(cluster, namespace, pod_name)


def check_online(cluster: K8sCluster) -> bool:
    try:
        list_pods(cluster)
        return True
    except Exception:
        return False
