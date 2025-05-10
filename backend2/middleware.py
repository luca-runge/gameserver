from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class CheckAPIKey(BaseHTTPMiddleware):
    def __init__(self, app, valid_keys):
        super().__init__(app)
        self.valid_keys = valid_keys

    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("Authorization")
        if not api_key or api_key not in self.valid_keys:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Unauthorized API Key"},
            )

        return await call_next(request)

