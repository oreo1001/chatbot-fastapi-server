import logging
import random
import time
import os
import traceback
import chardet
from fastapi import Request, Response
from fastapi.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

# Request 및 Response 로깅 미들웨어
class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger
    async def dispatch(self, request: Request, call_next):
        try:
            if(request.url.path !='/logs'): 
                body = await request.body()
                self.logger.info(f"Request: {request.method} {request.url}")
                self.logger.info(f"Request Body: {body.decode()}")
            response = await call_next(request)

            if request.url.path != '/logs' and 'static' not in request.url.path:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                if response_body:
                    self.logger.info(f"Response Body: {response_body.decode('utf-8', errors='ignore')}")
                return Response(content=response_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)
            return response
        except Exception as e:
            tb = traceback.format_exc()
            self.logger.error("Exception occurred: %s\n%s", str(e), tb)
            self.logger.exception(e)
            return Response(
                content=b"Internal Server Error",
                status_code=500,
                media_type="application/json"
            )

#test용
# while True:
#     random_number = random.randint(0, 10)
#     if random_number == 9:
#         logger.error(f"Random message generated: {random_number}")
#     elif random_number in [3, 5, 7]:
#         logger.warning(f"Random message generated: {random_number}")
#     else:
#         logger.info(f"Random message generated: {random_number}")
#     time.sleep(1)

            # response_body = [chunk async for chunk in response.body_iterator]
            # if response_body:
            #     logger.info(f"Response Body: {response_body[0].decode('utf-8',errors='ignore')}")
            # response.body_iterator = iterate_in_threadpool(iter(response_body))
            # logger.info(f"Response: {response.status_code}")