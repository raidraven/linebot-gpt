"""
LINE Bot — Flask webhook with OpenAI integration and simple in-memory conversation memory
- 環境変数: LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, OPENAI_API_KEY
- メモリ上にユーザーごとの会話履歴を保持（サーバー再起動で消える）
- 管理画面で「応答メッセージOFF」、WebhookをONにして使う
"""

import os
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not LINE_CHANNEL_SECRET or not LINE_CHANNEL_ACCESS_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("環境変数が正しく設定されていません。")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
app.config.update(DEBUG=False, TESTING=False)

# ユーザーごとの会話履歴をメモリで管理
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
        abort(400)
    except Exception:
        abort(500)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    user_text = event.message.text

    # ユーザー履歴がなければ作成
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # ユーザー発言を履歴に追加
    user_sessions[user_id].append({"role": "user", "content": user_text})

    # 会話履歴にシステムプロンプトを先頭に入れる
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_sessions[user_id]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply_text = response.choices[0].message.content.strip()
        # AI返答を履歴に追加
        user_sessions[user_id].append({"role": "assistant", "content": reply_text})
    except Exception:
        reply_text = "AI応答中にエラーが発生しました。しばらくしてから再度お試しください。"

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception:
        pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
