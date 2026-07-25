"""Deploy webhook: lets an external CI server (e.g. Jenkins) redeploy the app.

PythonAnywhere's free tier can't run Jenkins, cron, or any always-on process,
so CI lives elsewhere and simply calls this endpoint. On a valid request it:

    1. runs ``git pull --ff-only`` in the repo working tree,
    2. purges expired temp pastes,
    3. ``touch``es the WSGI file, which is how PythonAnywhere reloads a web app.

Security: the endpoint is disabled unless ``DEPLOY_TOKEN`` is configured, and
every request must present that exact token in the ``X-Deploy-Token`` header
(compared in constant time). It only ever runs a fixed ``git pull`` — never
input from the request — so there is no command-injection surface.
"""
import hmac
import os
import subprocess

from flask import Blueprint, current_app, jsonify, request

from ..extensions import limiter
from ..utils import purge_expired

deploy_bp = Blueprint("deploy", __name__)


def _git_env():
    """Copy the process env, adding the PythonAnywhere proxy if configured."""
    env = os.environ.copy()
    proxy = current_app.config.get("PA_PROXY")
    if proxy:
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
            env[key] = proxy
    return env


def _run(cmd, cwd, env):
    """Run a command, returning a JSON-friendly result dict."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env,
            capture_output=True, text=True, timeout=120,
        )
        return {
            "cmd": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"cmd": " ".join(cmd), "returncode": -1, "stdout": "", "stderr": str(exc)}


@deploy_bp.post("")
@limiter.limit("12 per hour")
def deploy():
    expected = current_app.config.get("DEPLOY_TOKEN")
    if not expected:
        return jsonify(error="Deploy endpoint is disabled (DEPLOY_TOKEN not set)"), 503

    provided = request.headers.get("X-Deploy-Token", "")
    if not hmac.compare_digest(provided, expected):
        return jsonify(error="Unauthorized"), 401

    repo_dir = current_app.config["DEPLOY_REPO_DIR"]
    env = _git_env()

    steps = [
        _run(["git", "pull", "--ff-only"], repo_dir, env),
    ]
    pull_ok = steps[-1]["returncode"] == 0

    # Sweep expired anonymous pastes while we're here (replaces the cron task).
    purged = None
    if pull_ok:
        try:
            purged = purge_expired()
        except Exception as exc:  # never let cleanup fail the deploy
            purged = f"skipped: {exc}"

    # Trigger the reload by touching the WSGI file (the PythonAnywhere idiom).
    reloaded = False
    wsgi_file = current_app.config.get("WSGI_FILE")
    if pull_ok and wsgi_file and os.path.exists(wsgi_file):
        try:
            os.utime(wsgi_file, None)
            reloaded = True
        except OSError as exc:
            steps.append({"cmd": f"touch {wsgi_file}", "returncode": -1,
                          "stdout": "", "stderr": str(exc)})

    status = "ok" if pull_ok else "failed"
    http = 200 if pull_ok else 500
    return jsonify(status=status, reloaded=reloaded, purged=purged, steps=steps), http
