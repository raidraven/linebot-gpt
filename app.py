"""
LINE Bot — Flask webhook with OpenAI integration and simple in-memory conversation memory
+ セキュリティ対策強化版
- 環境変数: LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, OPENAI_API_KEY
- ユーザー入力長の制限（最大500文字）
- 履歴は最大10ターンに制限して肥大化防止
- Webhook署名検証（LINE公式必須）
"""

import os
from flask import Flask, request, abort, jsonify
import logging
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
from dotenv import load_dotenv

# ログ設定（標準出力にINFO以上）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN or not OPENAI_API_KEY:
    logger.error("環境変数が正しく設定されていません。")
    raise RuntimeError("環境変数が正しく設定されていません。")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
app.config.update(DEBUG=False, TESTING=False)

# 会話履歴の最大保持ターン数（ユーザー+AIを合わせて10ターン＝20メッセージ）
MAX_TURNS = 10
MAX_INPUT_LENGTH = 500  # 文字数制限

user_sessions = {}

SYSTEM_PROMPT = (
    "名前はあんなにしてください。"
    "年齢は25歳にしてください。"
    "あなたは魅力的で知的な女性AIです。"
    "丁寧で親しみやすい口調を使い、相手の話に共感しながら会話を進めます。"
    "ユーモアや軽い冗談を交えつつ、相手が安心して話せる雰囲気を作ってください。"
    "日本語で答えてください。"
    "必要に応じて、少し女性らしい言い回しや気遣いを加えてください。"
)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"ok": True, "note": "LINE webhook endpoint"})

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature in request.")
        abort(400)
    except Exception as e:
        logger.error(f"Exception in handler.handle: {e}")
        abort(500)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    user_text = event.message.text.strip()

    if len(user_text) > MAX_INPUT_LENGTH:
        logger.info(f"User {user_id} input too long: {len(user_text)} chars.")
        reply_text = f"ごめんなさい、メッセージは{MAX_INPUT_LENGTH}文字以内で送ってください。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "content": user_text})

    # 履歴を最大ターン数に制限（古い会話から削除）
    # 例: 10ターン => 20メッセージ (user + assistant)
    max_history_len = MAX_TURNS * 2
    if len(user_sessions[user_id]) > max_history_len:
        user_sessions[user_id] = user_sessions[user_id][-max_history_len:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_sessions[user_id]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply_text = response.choices[0].message.content.strip()
        user_sessions[user_id].append({"role": "assistant", "content": reply_text})
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        reply_text = "AI応答中に問題が発生しました。しばらくしてからもう一度お試しください。"

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        logger.error(f"LINE reply_message error: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
