import yt_dlp
import requests
import os
from flask import Flask, request

app = Flask(__name__)

# 🔐 قراءة التوكنات من Environment Variables (آمن)
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

    # فيسبوك يسمح بحد أقصى 25MB
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
    filename = 'shadow_video.mp4'

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


# ------------------ Webhook ------------------
@app.route("/webhook", methods=['GET', 'POST'])
def webhook():

    # 🔹 مرحلة التحقق (Verify)
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification failed", 403

    # 🔹 استقبال الرسائل
    data = request.json

    try:
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):

                    if messaging_event.get("message"):

                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"].get("text", "").lower()

                        greetings = ["مرحبا", "سلام", "hi", "hello", "هلا"]

                        # ترحيب
                        if any(greet in message_text for greet in greetings):
                            send_text_message(
                                sender_id,
                                "أهلاً بك في Shadow Bot 🥷\nأرسل رابط فيديو وسأقوم بتحميله لك."
                            )

                        # معالجة رابط
                        elif "http" in message_text:
                            send_text_message(sender_id, "⏳ جاري التحميل...")

                            try:
                                file_path = download_video(message_text)
                                send_text_message(sender_id, "✅ تم التحميل، جاري الإرسال...")

                                if send_video_file(sender_id, file_path):
                                    send_text_message(sender_id, "🚀 تم الإرسال بنجاح!")
                                else:
                                    send_text_message(sender_id, "❌ الفيديو أكبر من 25MB.")

                                if os.path.exists(file_path):
                                    os.remove(file_path)

                            except:
                                send_text_message(sender_id, "⚠️ تعذر تحميل الفيديو. تأكد أن الرابط عام.")

    except:
        pass

    return "ok", 200


# ------------------ تشغيل السيرفر (مهم لـ Render) ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
