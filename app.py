import yt_dlp
import requests
import os
from flask import Flask, request

app = Flask(__name__)

# 🔐 قراءة التوكنات من Render
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


# ------------------ إرسال رسالة نصية ------------------
def send_text_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    requests.post(url, json=payload)


# ------------------ إرسال فيديو ------------------
def send_video_file(recipient_id, file_path):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"

    # حد فيسبوك 25MB
    if os.path.getsize(file_path) > 26000000:
        return False

    files = {
        'filedata': (os.path.basename(file_path), open(file_path, 'rb'), 'video/mp4')
    }

    params = {
        'recipient': '{"id": "' + recipient_id + '"}',
        'message': '{"attachment": {"type": "video", "payload": {}}}'
    }

    response = requests.post(url, params=params, files=files)
    return response.status_code == 200


# ------------------ تحميل الفيديو ------------------
def download_video(url):
    filename = "shadow_video.mp4"

    ydl_opts = {
        'format': 'best',
        'outtmpl': filename,
        'noplaylist': True,
        'quiet': False,
        'nocheckcertificate': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


# ------------------ Webhook ------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # 🔹 التحقق من فيسبوك
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if token == VERIFY_TOKEN:
            return challenge
        return "Verification failed", 403

    # 🔹 استقبال الرسائل
    data = request.json

    try:
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):

                    if event.get("message"):
                        sender_id = event["sender"]["id"]
                        text = event["message"].get("text", "").strip()

                        # ترحيب
                        if text.lower() in ["مرحبا", "سلام", "hi", "hello"]:
                            send_text_message(
                                sender_id,
                                "أهلاً بك 👋\nأرسل رابط فيديو وسأحاول تحميله لك."
                            )

                        # إذا كان رابط
                        elif "http" in text:
                            send_text_message(sender_id, "⏳ جاري التحميل...")

                            try:
                                file_path = download_video(text)
                                send_text_message(sender_id, "📤 جاري إرسال الفيديو...")

                                if send_video_file(sender_id, file_path):
                                    send_text_message(sender_id, "✅ تم الإرسال بنجاح!")
                                else:
                                    send_text_message(sender_id, "❌ الفيديو أكبر من 25MB.")

                                if os.path.exists(file_path):
                                    os.remove(file_path)

                            except Exception as e:
                                send_text_message(
                                    sender_id,
                                    f"⚠️ خطأ تقني أثناء التحميل:\n{str(e)}"
                                )

    except Exception as e:
        print("Webhook Error:", e)

    return "ok", 200


# ------------------ تشغيل السيرفر ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
