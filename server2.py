# server.py
from flask import Flask, request, abort
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from pyngrok import ngrok
import os
import logging
from dotenv import load_dotenv
from flask import Response

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
current_floor = 1

# ngrokトークン設定
NGROK_TOKEN = os.getenv("NGROK_TOKEN", "")
if NGROK_TOKEN:
    ngrok.set_auth_token(NGROK_TOKEN)
    ngrok.kill()

# --- 認証フィルター ---
@app.before_request
def verify_key():
    if request.method == "OPTIONS":
        return Response(status=200)
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
        socketio.emit('new_floor', {'floor': current_floor})
    else:
        logging.info("5階のため、押下指示は送信しません。")

@app.route("/api/request_press", methods=["POST", "OPTIONS"])
def api_request_press():
    global current_floor
    logging.info("[API] 外部からのボタン押下リクエストを受信しました。")

    if current_floor is None:
        logging.warning("[API] 階数情報がまだありません。")
        return {"status": "error", "message": "階数情報が未設定です。"}, 400

    if current_floor != 5:
        logging.info(f"[API] 現在の階数は{current_floor}階です。press_button をブロードキャストします。")
        socketio.emit('press_button')
        return {"status": "success", "message": "押下指示を送信しました。"}, 200
    else:
        logging.info("[API] 5階のため、押下指示は送信しません。")
        return {"status": "skipped", "message": "5階なので押下処理をスキップしました。"}, 200


# --- メイン ---
if __name__ == '__main__':
    # ngrokトンネルを開く
    public_url = ngrok.connect(5000, bind_tls=True)
    logging.info(f"ngrokトンネルを開きました: {public_url} → http://127.0.0.1:5000")

    # サーバーを全てのIPで起動（外部アクセス可能にする）
    socketio.run(app, host="0.0.0.0", port=5000)
