"""HTTP 响应工具"""
import json
from datetime import datetime, date
from fastapi.responses import JSONResponse


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def ok(data: dict, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        content=json.loads(json.dumps(data, default=_json_default)),
        status_code=status_code,
    )
