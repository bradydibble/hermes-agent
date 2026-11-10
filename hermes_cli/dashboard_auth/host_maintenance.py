"""Same-user retirement of a standalone serve, using its private rendezvous token."""

from starlette.responses import JSONResponse

HEADER = "x-hermes-maintenance-token"
_OPERATIONS = frozenset({
    ("GET", "/api/host/identity"),
    ("GET", "/api/health/idle"),
    ("POST", "/api/health/retirement"),
})


def authenticate_host_maintenance(request):
    """A 0600 host token permits only local lifecycle operations, even behind cookie auth.

    Reject proxy/browser traffic rather than treating a proxy's loopback connection as a
    local operator. The credential is never placed in a query string or browser cookie.
    """
    tokens = request.headers.getlist(HEADER)
    if not tokens:
        return None
    import hmac
    from hermes_cli import web_server

    peer = request.client
    allowed = (
        len(tokens) == 1
        and getattr(request.app.state, "host_role", None) == "serve"
        and (request.method, request.url.path) in _OPERATIONS
        and peer is not None and peer.host in {"127.0.0.1", "::1"}
        and not any(k == "origin" or k == "forwarded" or k.startswith("x-forwarded-")
                    for k in request.headers)
        and bool(tokens[0])
        and hmac.compare_digest(tokens[0].encode(), web_server._SESSION_TOKEN.encode())
    )
    if not allowed:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    request.state.host_maintenance_authenticated = True
    request.state.token_authenticated = True
    return None
