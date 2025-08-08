from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from openai import OpenAI
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込む
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 環境変数がすべて設定されているか確認
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET or not OPENAI_API_KEY:
    raise ValueError("環境変数が正しく設定されていません。")

# Flaskアプリケーション作成
app = Flask(__name__)

# LINE Messaging APIインスタンス
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

# Webhookハンドラー
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# OpenAIクライアント（新SDK）
client = OpenAI(api_key=OPENAI_API_KEY)

# LINEのWebhookエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    except Exception as e:
        return f'Error: {str(e)}', 500

    return 'OK'

# メッセージ受信時の処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    print(f"受信メッセージ: {user_text}")

    try:
        # OpenAIにリクエスト（新SDK）
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 安価で速いモデル（必要ならgpt-3.5-turboに変更可）
            messages=[
                {
                    "role": "system",
                    "content": (
                        "名前はあんなにしてください。"
                        "年齢は25歳にしてください。"
                        "あなたは魅力的で知的な女性AIです。"
                        "丁寧で親しみやすい口調を使い、相手の話に共感しながら会話を進めます。"
                        "ユーモアや軽い冗談を交えつつ、相手が安心して話せる雰囲気を作ってください。"
                        "日本語で答えてください。"
                        "必要に応じて、少し女性らしい言い回しや気遣いを加えてください。"
                    )
                },
                {"role": "user", "content": user_text}
            ]
        )

        reply_text = response.choices[0].message.content.strip()
        print(f"AI応答: {reply_text}")

    except Exception as e:
        print(f"OpenAIエラー: {e}")
        reply_text = "AI応答中にエラーが発生しました。しばらくしてから再度お試しください。"

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
