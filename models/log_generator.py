import logging
import random
import time
import os
import chardet
from fastapi import Request
from fastapi.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

def log_config():
    #경로 설정
    real_path = os.path.realpath(__file__)
    dir_path = os.path.dirname(real_path)
    parent_dir = os.path.dirname(dir_path)
    # 로그 파일 경로를 상위 디렉토리에 설정
    LOGFILE = os.path.join(parent_dir, 'app.log')
    print(LOGFILE)

    #로그 형식 등 설정
    logger = logging.getLogger("log_app")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:  #이거 없으면 두번씩 출력됨 핸들러땜에
        file_handler = logging.FileHandler(LOGFILE)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger

logger = log_config()

# Request 및 Response 로깅 미들웨어
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if(request.url.path !='/'): 
            body = await request.body()
            logger.info(f"Request: {request.method} {request.url}")
            logger.info(f"Request Body: {body.decode()}")

        response = await call_next(request)

        if(request.url.path !='/'): 
            response_body = [chunk async for chunk in response.body_iterator]
            # result = chardet.detect(response_body)
            # encoding = result['encoding']
            # decoded_text = response_body.decode(encoding)
            # if response_body:
            #     logger.info(f"Response Body: {decoded_text}")
            if response_body:
                logger.info(f"Response Body: {response_body[0].decode('utf-8',errors='ignore')}")
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            # logger.info(f"Response: {response.status_code}")
        return response

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