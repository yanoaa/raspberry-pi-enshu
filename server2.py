# server.py
from flask import Flask, request, abort
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from pyngrok import ngrok
import os
import logging
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# FlaskアプリとSocketIOの初期化
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# CORS設定
CORS(
    app,
    origins=os.getenv("ALLOWED_ORIGINS", "*"),
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-KEY", "Content-Type"]
)

# APIキー設定（.envから）
API_KEY = os.getenv("API_KEY", "changeme")

# グローバル変数
current_floor = None

# ngrokトークン設定
NGROK_TOKEN = os.getenv("NGROK_TOKEN", "")
if NGROK_TOKEN:
    ngrok.set_auth_token(NGROK_TOKEN)
    ngrok.kill()

# --- 認証フィルター ---
@app.before_request
def verify_key():
    if request.method == "OPTIONS":
        return
    if request.headers.get("X-API-KEY") != API_KEY:
        abort(401)

# --- WebSocketイベント ---
@socketio.on('connect')
def handle_connect():
    logging.info("クライアントが接続しました。")

@socketio.on('disconnect')
def handle_disconnect():
    logging.info("クライアントが切断しました。")

@socketio.on('update_floor')
def handle_floor_update(data):
    global current_floor
    floor = data.get('floor')
    if floor is not None:
        current_floor = floor
        logging.info(f"階数を更新: {current_floor}階")
        socketio.emit('new_floor', {'floor': current_floor})

@socketio.on('request_press')
def handle_press_request():
    logging.info("Pi-Roomからボタン押下リクエストを受信しました。")
    if current_floor is None:
        logging.warning("階数情報がまだありません。")
        return
    if current_floor != 5:
        logging.info(f"現在の階数は{current_floor}階です。Pi-Elevatorに押下指示を送信します。")
        socketio.emit('press_button')
    else:
        logging.info("5階のため、押下指示は送信しません。")

# --- メイン ---
if __name__ == '__main__':
    # ngrokトンネルを開く
    public_url = ngrok.connect(5000, bind_tls=True)
    logging.info(f"ngrokトンネルを開きました: {public_url} → http://127.0.0.1:5000")

    # サーバーを全てのIPで起動（外部アクセス可能にする）
    socketio.run(app, host="0.0.0.0", port=5000)
