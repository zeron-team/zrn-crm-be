"""WhatsApp proxy – forwards requests to the Node.js WhatsApp microservice on port 3001."""
import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

WA_SERVICE = "http://127.0.0.1:3001"


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_whatsapp(path: str, request: Request):
    """Transparent proxy to WhatsApp Node.js microservice."""
    url = f"{WA_SERVICE}/{path}"
    if request.url.query:
        url += f"?{request.url.query}"

    body = await request.body()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length", "transfer-encoding")}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            content=body if body else None,
            headers=headers,
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={k: v for k, v in resp.headers.items()
                 if k.lower() not in ("transfer-encoding", "content-encoding", "content-length")},
        media_type=resp.headers.get("content-type"),
    )
