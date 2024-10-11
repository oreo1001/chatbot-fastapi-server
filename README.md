# Sapie Chatbot FastAPI Server

Flask 서버 FastAPI로 마이그레이션 

FastAPI 비동기 로깅 페이지 만들어서 template 붙이기 
(Websocket으로 구현)

모델 등은 최대한 객체화

# 가상환경 설치후 다운로드
python -m venv venv <br>
source ./venv/Scripts/activate <br>
pip install -r requirements.txt <br>

# 서버 실행
uvicorn main:app --reload
