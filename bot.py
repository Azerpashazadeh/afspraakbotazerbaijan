import os
import sys
from flask import Flask, request
import requests

app = Flask(__name__)


def log(*args):
    print(*args, flush=True)
    sys.stdout.flush()

# --- AYARLAR ---
TOKEN = os.environ.get("TOKEN", "")   # Meta access token (Railway Variables'tan gelir)
PHONE_NUMBER_ID = "1148053611735379"  # senin Phone Number ID'in
VERIFY_TOKEN = "randevu2026"          # webhook doğrulama şifresi
# ----------------

# Basit hafıza: kim hangi aşamada
kullanici_durumu = {}


def mesaj_gonder(kime, metin):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}",
               "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": kime,
            "type": "text", "text": {"body": metin}}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=10)
        log("GONDERILDI:", kime, "->", r.status_code, r.text[:200])
    except Exception as e:
        log("GONDERME HATASI:", e)


@app.route("/webhook", methods=["GET"])
def dogrula():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Xəta", 403


@app.route("/webhook", methods=["POST"])
def gelen():
    data = request.get_json()
    try:
        deger = data["entry"][0]["changes"][0]["value"]

        # Gelen mesaj yoksa (status bildirimi vs.) sessizce çık
        if "messages" not in deger:
            return "OK", 200

        mesaj = deger["messages"][0]

        # Sadece text mesajlarını işle
        if mesaj.get("type") != "text":
            return "OK", 200

        gonderen = mesaj["from"]
        metin = mesaj["text"]["body"].strip().lower()
        durum = kullanici_durumu.get(gonderen, "yeni")

        log("GELEN:", gonderen, "metin:", metin, "durum:", durum)

        # 1) "salam" / "randevu" -> HER ZAMAN baştan başlat
        if metin in ["salam", "randevu", "salamlar", "hi", "start", "menu"]:
            cevap = ("Salam! 👋 Randevu üçün gün seçin:\n\n"
                     "1️⃣ Bazar ertəsi\n"
                     "2️⃣ Çərşənbə\n"
                     "3️⃣ Cümə\n\n"
                     "Rəqəm yazın (1, 2 və ya 3).")
            kullanici_durumu[gonderen] = "gun_secildi"

        # 2) Gün seçimi
        elif durum == "gun_secildi" and metin in ["1", "2", "3"]:
            gunler = {"1": "Bazar ertəsi", "2": "Çərşənbə", "3": "Cümə"}
            secilen = gunler[metin]
            cevap = ("Saat seçin:\n\n"
                     "A) 10:00\n"
                     "B) 14:00\n"
                     "C) 17:00\n\n"
                     "Hərf yazın (A, B və ya C).")
            kullanici_durumu[gonderen] = f"gun:{secilen}"

        # 3) Saat seçimi -> randevu tamam
        elif durum.startswith("gun:") and metin in ["a", "b", "c"]:
            saatler = {"a": "10:00", "b": "14:00", "c": "17:00"}
            secilen_gun = durum.split(":", 1)[1]
            secilen_saat = saatler[metin]
            cevap = (f"✅ Randevunuz qeydə alındı!\n\n"
                     f"📅 Gün: {secilen_gun}\n"
                     f"🕐 Saat: {secilen_saat}\n\n"
                     f"Təşəkkür edirik! Yeni randevu üçün 'salam' yazın.")
            kullanici_durumu[gonderen] = "yeni"

        # 4) Anlaşılmayan mesaj
        else:
            cevap = "Randevu almaq üçün 'salam' yazın. 😊"
            kullanici_durumu[gonderen] = "yeni"

        mesaj_gonder(gonderen, cevap)

    except (KeyError, IndexError) as e:
        log("ISLEME HATASI:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
