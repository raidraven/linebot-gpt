from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
import openai
from dotenv import load_dotenv
import os

# .envファイルから環境変数を読み込む
load_dotenv()
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")  # LINEチャネルアクセストークン
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")              # LINEチャネルシークレット
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")                        # OpenAI APIキー

# 環境変数がすべて設定されているか確認
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET or not OPENAI_API_KEY:
    raise ValueError("環境変数が正しく設定されていません。")

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)
# LINE Messaging APIのインスタンスを作成
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
# Webhookハンドラーのインスタンスを作成
handler = WebhookHandler(LINE_CHANNEL_SECRET)
# OpenAIのAPIキーを設定
openai.api_key = OPENAI_API_KEY

# LINEプラットフォームからのWebhookイベントを受け取るエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')  # リクエストヘッダーから署名を取得
    body = request.get_data(as_text=True)                    # リクエストボディを取得

    try:
        handler.handle(body, signature)                      # イベントハンドラーで処理
    except InvalidSignatureError:
        return 'Invalid signature', 400                      # 署名が不正な場合は400を返す
    except Exception as e:
        return f'Error: {str(e)}', 500                       # その他のエラーは500を返す
    return 'OK'

# テキストメッセージイベントを処理するハンドラー
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    print(f"受信メッセージ: {user_text}")

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは親切なAIです。必ず日本語で答えてください。"},
                {"role": "user", "content": user_text}
            ]
        )
        reply_text = response.choices[0].message.content
        print(f"AI応答: {reply_text}")
    except Exception as e:
        print(f"OpenAIエラー: {e}")
        reply_text = "AI応答中にエラーが発生しました。しばらくしてから再度お試しください。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    # デバッグモードは本番環境ではFalseにしてください
    app.run(host="0.0.0.0", port=5000, debug=False)
