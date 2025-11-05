import time
from starlette.middleware.base import BaseHTTPMiddleware
import logging

# Configura o logger
logging.basicConfig(
    filename="api_logs.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class LogRequestsMiddleware(BaseHTTPMiddleware):
    """Middleware que registra todas as requisições HTTP da API."""

    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        log_message = (
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"{process_time:.3f}s"
        )
        logging.info(log_message)

        return response
