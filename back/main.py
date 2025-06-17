import google.generativeai as genai
import os
import sqlite3
import random
import string
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr 
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import smtplib # 이메일 전송을 위한 라이브러리
from email.mime.text import MIMEText # 이메일 내용 작성을 위한 라이브러리
from dotenv import load_dotenv # .env 파일 로드

# --- .env 파일 로드 (환경 변수) ---
load_dotenv()

# --- FastAPI 애플리케이션 초기화 ---
app = FastAPI(
    title="고백 시나리오 생성 및 전송 API",
    description="17세 고등학생을 위한 고백 멘트와 시나리오, 거절 시 대처법을 생성하고 이메일로 전송합니다." 
)

# --- CORS 미들웨어 추가 ---
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5501",
    "http://127.0.0.1:5500",
    "null"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 보안 코드 로직
# --- SQLite 데이터베이스 설정 ---
DATABASE_NAME = "codes.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE
        )
    """)
    conn.commit()
    conn.close()

# --- SQLite에서 가장 최신 코드를 가져오는 함수 ---
def get_latest_code_from_db():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        # id가 가장 큰 (가장 나중에 삽입된) 코드를 선택
        cursor.execute("SELECT code FROM codes ORDER BY id DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            print(f"DEBUG: DB에서 가져온 최신 코드: {result[0]}")
            return result[0] 
        return None
    except sqlite3.Error as e:
        print(f"데이터베이스에서 최신 코드를 가져오는 중 오류 발생: {e}")
        return None
    finally:
        if conn:
            conn.close()


# --- 코드 생성을 위한 Pydantic 모델 ---
class CodeGenerationResponse(BaseModel):
    code: str = Field(..., example="123456")
    message: str = Field(..., example="코드가 성공적으로 생성 및 저장되었습니다.")


# --- Gemini API 설정 ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError("오류: 'GOOGLE_API_KEY' 환경 변수가 설정되어 있지 않습니다.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')


# --- 이메일 전송을 위한 환경 변수 로드 ---
SENDER_EMAIL = os.getenv("EMAIL_ADDRESS")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

if not all([SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER]):
    print("경고: 이메일 전송 환경 변수(EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER)가 설정되지 않았습니다. 이메일 전송 API가 작동하지 않을 수 있습니다.")


# --- 데이터 모델 정의 (Pydantic) ---
class UserInfo(BaseModel):
    name: str = Field(..., example="전유림")
    age: int = Field(..., example=17)
    personality: str = Field(..., example="외향적, 밝고 허당미 있음")
    likes: List[str] = Field(..., example=["고양이", "노래 듣기", "한강 따라 산책"])

class CrushInfo(BaseModel):
    name: str = Field(..., example="육준성")
    age: int = Field(..., example=17)
    personality: str = Field(..., example="무뚝뚝하지만 나에겐 다정함, 따뜻하고 똑똑함")
    likes: List[str] = Field(..., example=["스포츠", "피아노", "조용한 카페에서 작업하기"])

class ConfessionRequest(BaseModel):
    user_info: UserInfo
    crush_info: CrushInfo
    sum_period: str = Field(..., example="2주")
    confession_method: str = Field(..., example="만나서 직접")

# --- 이메일 전송 요청을 위한 새로운 모델 ---
class EmailSendRequest(BaseModel):
    recipient_email: EmailStr = Field(..., example="recipient@example.com") 
    scenario_text: str = Field(..., example="고백 시나리오 내용...")


# --- 답변 생성 API ---
async def generate_confession_text(user_info: UserInfo, crush_info: CrushInfo, sum_period: str, confession_method: str) -> str:
    prompt = f"""
    당신은 지금부터 **17세 고등학생을 위한 고백 전문가**입니다. 저에게 고백 상황에 대한 정보를 주시면, 그 정보를 바탕으로 상대방에게 고백할 **고백 멘트**와 **고백 계획**, 그리고 **거절당했을 경우의 대처 멘트**를 구성하여 상세하게 알려드리겠습니다. 답변은 항상 **정중한 존댓말**로 작성해 주세요.

    ---

    ### **출력 지침:**

    1.  **고백 멘트**:
        * "{crush_info.name}아,"로 시작해야 합니다.
        * **100자 이내**로, 진심이 담기고 자연스러운 고등학생 말투로 작성해 주세요. (고백 멘트 자체는 고백 당사자의 말투이므로 반말 유지)
        * 지나치게 오글거리거나 과장된 표현은 피하고, 따뜻하고 진솔한 느낌이 들도록 해 주세요.
    2.  **고백 계획**:
        * 총 **3단계**로 나누어 구성해 주세요.
        * 각 단계는 **100자 이내**로 간결하게 작성해 주세요.
        * 현실적이고 실행 가능한 고등학생 수준의 계획이어야 합니다.
        * 설명을 할 때는 **존댓말**을 사용해 주세요.
    3.  **거절 시 대처 방안**:
        * **200자 이내**로 작성해 주세요.
        * 다음 두 가지 요소를 반드시 포함해야 합니다:
            * **상대방에게 할 말**: 담담하고 쿨하게 상황을 받아들이며 관계 유지를 원하는 멘트를 고등학생 말투로 작성해주세요. (반말 사용)
            * **스스로를 다독이는 내용**: 자신의 감정에 솔직했던 것에 대한 긍정적인 평가와 함께 스스로를 격려하는 내용을 포함해 주세요.
        * 실제 대화처럼 길게 늘어지는 구체적인 대사나 행동 지시(예: 'ㅋㅋㅋ', '어깨 툭 치기', '속으로')는 절대 포함하지 마십시오.
        * 담담하고 차분한 톤으로 작성하며, 오글거리거나 장난스러운 표현은 피하도록 안내해 주세요.
        * 설명을 할 때는 **존댓말**을 사용해 주세요.
    4.  **어떠한 서두나 인사말도 없이, 바로 '고백 멘트:', '고백 계획:', '거절 시 대처 방안:' 순서로 내용을 시작해주세요.**
    5.  **고백 계획에는 '*'을 넣지 마세요.**

    ---

    ### **사용자가 입력한 정보 (이 정보를 바탕으로 시나리오를 생성해 주세요):**

    내 이름 : {user_info.name}
    나이 : {user_info.age}세
    성격 : {user_info.personality}
    좋아하는 것 : {', '.join(user_info.likes)}
    상대 이름 : {crush_info.name}
    나이 : {crush_info.age}세
    성격 : {crush_info.personality}
    좋아하는 것 : {', '.join(crush_info.likes)}
    썸 탄 기간 : {sum_period}
    고백 방식 : {confession_method}

    ---
    ### **출력 예시:**

    고백 멘트 :
    준성아, 한 달 동안 같이 지내면서 너랑 이야기하고, 웃고, 같이 있는 시간이 너무 좋았어.
    너 생각하면 나도 모르게 웃음이 나고, 하루가 더 기대돼. 그래서 말하려고 해. 너를 더 알고 싶고, 더 가까워지고 싶어. 나랑 진지하게 만나볼래?

    고백 계획 :
    1. 자연스러운 약속 잡기: ...
    2. 공통점으로 분위기 풀기: ...
    3. 진심을 담아 고백하기: ...

    거절 시 대처 방안 :
    "괜찮아! 그냥 제 마음 솔직하게 전하고 싶었어요. 그래도 앞으로 우리 둘이 편하게 지내는 건 변함없겠죠?"라고 말하며 쿨한 모습을 보여주세요. ...

    ---
    ### **참고 고백 멘트 풀 (아래 멘트들을 참고하여 새로운 멘트 하나를 생성하세요):**
    * 민준아, 처음 만났을 때 너가 수학숙제 도와준 것도, 급식실에서 우유 대신 네가 준 간식도 아직 생각나. 그런 작은 순간마다 네가 내 맘속에 스며들었어. 웃을 때마다 내 하루가 더 밝아졌어. 이런 나의 진심, 너에게 전하고 싶어. 나 너를 좋아해.
    * 유림아, 너랑 대화하고, 같이 공부하고, 영화 얘기할 때마다 나도 뭔가 더 나은 사람 되는 기분이야. 네가 있어서 공부도 더 재미있고, 하루가 더 충실해. 이런 너에게 솔직해지고 싶어서. 앞으로도 네 옆에서 함께 있고 싶어. 나, 네가 정말 좋아.
    * 시웅아, 네가 웃는 모습을 보면 햇살 같아서, 어두웠던 하루도 환해져. 네 목소리가 하루의 배경음악 같아서, 그냥 들어도 기분이 좋아. 그래서 오늘 이렇게 솔직해지려고 해. 나, 너를 좋아해.
    * 정원아, 솔직히 너한테 고백하는 거 떨려. 근데 이 마음 전하지 않으면 후회할 것 같아서 용기 냈어. 나 너 좋아해!
    * 민재야, 널 처음 봤을 때부터 뭔가 끌렸어. 같이 있으면 시간 가는 줄 모르겠고, 매일매일 더 좋아지는 것 같아. 내 마음 받아줄래?
    """
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"Gemini API 호출 중 오류가 발생했습니다: {e}")

@app.post("/generate-confession", summary="고백 시나리오 생성", response_description="생성된 고백 시나리오 텍스트")
async def create_confession(request_data: ConfessionRequest):
    try:
        scenario_text = await generate_confession_text(
            request_data.user_info,
            request_data.crush_info,
            request_data.sum_period,
            request_data.confession_method
        )
        return {"scenario": scenario_text}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시나리오 생성 중 알 수 없는 오류가 발생했습니다: {e}")


# --- 이메일 전송 API ---
@app.post("/send-email", summary="고백 시나리오 이메일 전송", response_description="이메일 전송 결과 메시지")
async def send_confession_email(email_request: EmailSendRequest):
    if not all([SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER]):
        raise HTTPException(status_code=500, detail="이메일 전송을 위한 서버 설정이 완료되지 않았습니다.")

    latest_code = get_latest_code_from_db()

    # 이메일 본문을 HTML 형식으로 구성 (plain타입보다 효과적임)
    email_body_html = f"""
    <html>
    <body>
        <p>안녕하세요! 당신을 위한 편지가 도착했습니다.</p>
        <p>이 시나리오를 통해 좋은 결과가 있기를 진심으로 바랍니다.</p>
        
        <hr/>
        <h3>고백_Go의 편지</h3>
        <pre>{email_request.scenario_text}</pre>
        <hr/>
        
        <h3>중요: 당신의 보안 코드</h3>
        <p>이 코드는 편지 보관함에서 시나리오를 다시 확인할 때 필요합니다.</p>
        <p>잊어버리지 않도록 잘 보관해주세요.</p>
        
        <p><strong>[보안 코드]: <span style="font-size: 1.2em; color: #007bff;">{latest_code if latest_code else '코드를 불러올 수 없습니다.'}</span></strong></p>
        
        <hr/>
        <p>행운을 빌어요!!</p>
    </body>
    </html>
    """

    msg = MIMEText(email_body_html, 'html', 'utf-8') # plain -> html 변경
    msg['Subject'] = '💌 당신의 특별한 고백 편지가 도착했어요! 💌'
    msg['From'] = SENDER_EMAIL
    msg['To'] = email_request.recipient_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return {"message": "이메일이 성공적으로 전송되었습니다!"}
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=500, detail="이메일 인증에 실패했습니다. 발신자 계정 정보 또는 앱 비밀번호를 확인해주세요.")
    except smtplib.SMTPConnectError:
        raise HTTPException(status_code=500, detail=f"SMTP 서버에 연결할 수 없습니다. 서버 주소({SMTP_SERVER})와 포트({SMTP_PORT})를 확인해주세요.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 전송 중 오류가 발생했습니다: {e}")
    

# --- 무작위 6자리 숫자 코드 생성 및 저장 API ---
@app.post("/generate-code", summary="무작위 6자리 코드 생성 및 저장", response_description="생성된 코드와 저장 결과 메시지")
async def generate_and_store_code():
    try:
        # 6자리 무작위 숫자 코드 생성 (중복 방지를 위해 루프)
        new_code = ""
        while True:
            new_code = ''.join(random.choices(string.digits, k=6))
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT code FROM codes WHERE code = ?", (new_code,))
            if not cursor.fetchone(): # 중복되는 코드가 없으면 루프 탈출
                break
            conn.close()

        # SQLite에 코드 저장
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO codes (code) VALUES (?)", (new_code,))
        conn.commit()
        conn.close()

        return CodeGenerationResponse(code=new_code, message="코드가 성공적으로 생성 및 저장되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"코드 생성 및 저장 중 오류가 발생했습니다: {e}")
    

# --- 코드 확인을 위한 Pydantic 모델 ---
class CodeCheckRequest(BaseModel):
    input_code: str = Field(..., example="123456", min_length=6, max_length=6)

class CodeCheckResponse(BaseModel):
    exists: bool = Field(..., example=True)
    message: str = Field(..., example="코드가 데이터베이스에 존재합니다.")


# --- 입력된 코드 확인 API ---
@app.post("/check-code", summary="입력된 코드가 DB에 존재하는지 확인", response_description="코드 존재 여부 (True/False)")
async def check_code_exists(request: CodeCheckRequest):
    input_code = request.input_code

    if not input_code.isdigit() or len(input_code) != 6:
        raise HTTPException(status_code=400, detail="유효한 6자리 숫자 코드를 입력해야 합니다.")

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM codes WHERE code = ?", (input_code,))
        
        # 결과가 있으면 True (편지 작성 성공)
        code_exists = cursor.fetchone() is not None
        
        message = "코드가 데이터베이스에 존재합니다." if code_exists else "코드가 데이터베이스에 존재하지 않습니다."
        
        return CodeCheckResponse(exists=code_exists, message=message)
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"알 수 없는 오류가 발생했습니다: {e}")
    finally:
        if conn:
            conn.close()


# python 명령어로 실행
if __name__ == "__main__":
    init_db() # 앱 시작 시 DB 초기화
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)