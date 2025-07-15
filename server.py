# server.py
# 必要なライブラリをインポート
from flask import Flask, jsonify
import requests
import logging

from pyngrok import ngrok

import os
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()  

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ここだけ追加・修正 ---
NGROK_TOKEN = "2wuVwoWrfiid4G8sajbTD2bYWwg_6kz4pxcFixLp7GcLgR1EU"
ngrok.set_auth_token(NGROK_TOKEN)

# 既存 ngrok プロセスを強制終了
ngrok.kill()
# --- ここまで ---

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

CORS(app, origins=os.getenv("ALLOWED_ORIGINS", "*"))
API_KEY = os.getenv("API_KEY", "changeme")


# 認証チェックを追加
from flask import request, abort
@app.before_request
def verify_key():
    if request.endpoint == "health":  # 死活監視用は除外
        return
    if request.headers.get("X-API-KEY") != API_KEY:
        abort(401)


# Pi-ElevatorのIPアドレスとポートを設定
# (注: 実際の環境に合わせて変更してください)
PI_ELEVATOR_IP = "172.20.10.14"
PI_ELEVATOR_PORT = 5001
PI_ELEVATOR_URL = f"http://{PI_ELEVATOR_IP}:{PI_ELEVATOR_PORT}/press"

@app.route('/call', methods=['POST'])
def handle_call():
    """
    Pi-Roomからの呼び出しを受け付け、Pi-Elevatorに処理を依頼するエンドポイント
    """
    logging.info("Pi-Roomからの呼び出しリクエストを受信しました。")
    
    try:
        # Pi-Elevatorに押下要求を送信 (タイムアウトを5秒に設定)
        logging.info(f"{PI_ELEVATOR_URL} にリクエストを送信します。")
        response = requests.post(PI_ELEVATOR_URL, timeout=20)
        
        # Pi-Elevatorからの応答ステータスコードをチェック
        response.raise_for_status()  # 200番台以外の場合、HTTPErrorを発生させる

        elevator_data = response.json()
        elevator_result = elevator_data.get("result", "unknown")
        logging.info(f"Pi-Elevatorからの応答: {elevator_result}")
        
        # 成功応答をPi-Roomに返す
        return jsonify({
            "status": "success",
            "elevator_result": elevator_result
        })

    except requests.exceptions.RequestException as e:
        # 通信エラー（タイムアウト、接続拒否など）
        logging.error(f"Pi-Elevatorとの通信に失敗しました: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to communicate with Pi-Elevator."
        }), 500 # サーバー内部エラーを示す500を返す

if __name__ == '__main__':

    public_url = ngrok.connect(5000, bind_tls=True)
    print(f" * ngrok tunnel {public_url} -> http://127.0.0.1:5000")

    # サーバーを起動 (LAN内のすべてのIPアドレスからアクセス可能にする)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)