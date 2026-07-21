"""Which machine a request came from, for presenter-only routes.

The backend binds localhost. The only remote path to it is the dev
server proxy on the presenter's machine (vite for the board, the deck's
own proxy), and both are configured to overwrite X-Forwarded-For with
the peer address they actually accepted the connection from, then
append via xfwd. The LAST entry is therefore the one hop our own
infrastructure vouches for; anything before it is client-supplied text.
Trusting the first entry was spoofable: vite appends to an existing
header, so a LAN client sending "X-Forwarded-For: 127.0.0.1" used to
arrive as "127.0.0.1, <lan-ip>" and read as loopback.

This assumption dies if the backend is ever bound to a LAN interface
directly: a direct connection controls its own header entirely. Keep
the bind on localhost or revisit this module first.
"""

from fastapi import HTTPException, Request

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def effective_client_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.rsplit(",", 1)[-1].strip()
    return request.client.host if request.client is not None else ""


def require_presenter_machine(request: Request, activity: str) -> None:
    """403 unless the request originates on the presenter's machine.

    The full-room guardrail: one presenter spends provider budget and
    presenter-machine compute; forty attendee browsers cannot, whatever
    their UI shows."""
    if effective_client_host(request) not in _LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=403,
            detail=f"{activity} is presenter-controlled and runs only "
            "from the presenter's machine",
        )
