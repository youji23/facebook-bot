import yt_dlp
import requests
import os
from flask import Flask, request

app = Flask(__name__)

# --- إعدادات البوت ---
PAGE_ACCESS_TOKEN = 'PAGE_ACCESS_TOKEN'
VERIFY_TOKEN = 'VERIFY_TOKEN'

def send_text_message(recipient_id, message_text):
    """إرسال رسالة نصية بسيطة"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    requests.post(url, json=payload)

def send_video_file(recipient_id, file_path):
    """إرسال ملف الفيديو الفعلي"""
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    
    # التأكد من حجم الملف (فيسبوك يسمح بـ 25MB كحد أقصى)
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

def download_video(url):
    """تحميل الفيديو باستخدام yt-dlp"""
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

@app.route("/", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Shadow Server Is Running!"

    # استقبال البيانات من فيسبوك
    data = request.json
    try:
        if data["object"] == "page":
            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"].get("text", "").lower()

                        # 1. نظام الترحيب
                        greetings = ["مرحبا", "سلام", "hi", "hello", "هلا"]
                        if any(greet in message_text for greet in greetings):
                            send_text_message(sender_id, "أهلاً بك في Shadow Bot! 🥷\nأرسل لي أي رابط فيديو (TikTok, FB, YT, Insta) وسأقوم بتحميله لك فوراً.")

                        # 2. نظام معالجة الروابط
                        elif "http" in message_text:
                            send_text_message(sender_id, "⏳ جاري معالجة الرابط.. انتظر قليلاً")
                            
                            try:
                                file_path = download_video(message_text)
                                send_text_message(sender_id, "✅ تم التحميل، جاري إرسال الفيديو...")
                                
                                # محاولة إرسال الملف
                                if send_video_file(sender_id, file_path):
                                    send_text_message(sender_id, "تم الإرسال بنجاح! 🚀")
                                else:
                                    send_text_message(sender_id, "❌ فشل الإرسال: حجم الفيديو يتجاوز 25MB.")
                                
                                # حذف الملف من الهاتف لتوفير مساحة
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            
                            except Exception as e:
                                send_text_message(sender_id, "⚠️ عذراً، لم أتمكن من تحميل هذا الفيديو. تأكد من أن الرابط عام وليس لحساب خاص.")
    except:
        pass

    return "ok", 200

if __name__ == "__main__":
    # تشغيل السيرفر على المنفذ 5000
    app.run(host='0.0.0.0', port=5000)
