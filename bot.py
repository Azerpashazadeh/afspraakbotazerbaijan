from flask import Flask, request, render_template_string, jsonify
import requests
import os
import json
import threading
import time as _time
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============================================================
#  MUSTERI AYARLARI
# ============================================================
BEDRIJF_NAAM = "Salon Test"
HEADER_AFBEELDING = ""
STANDAARD_TAAL = "az"

TALEN = [
    {"code": "az", "naam": "\U0001F1E6\U0001F1FF Azərbaycan"},
    {"code": "ru", "naam": "\U0001F1F7\U0001F1FA Русский"},
    {"code": "tr", "naam": "\U0001F1F9\U0001F1F7 Türkçe"},
    {"code": "en", "naam": "\U0001F1EC\U0001F1E7 English"},
]

T = {
    "az": {
        "kies_taal": "Dil seçin:",
        "welkom": "{bedrijf}-ə xoş gəlmisiniz! Nə vaxt gəlmək istəyirsiniz?",
        "kies_periode": "Dövr seçin",
        "kies_dag": "Gün seçin",
        "kies_dag_body": "Gün seçin:",
        "kies_tijd": "Vaxt seçin",
        "kies_tijd_body": "Vaxt seçin:",
        "geen_dagen": "Bu dövrdə boş gün yoxdur. Yenidən seçmək üçün mesaj göndərin.",
        "dag_vol": "Bu gün doludur. Başqa gün seçmək üçün mesaj göndərin.",
        "net_bezet": "Təəssüf, bu vaxt indicə doldu. Yenidən seçmək üçün mesaj göndərin.",
        "gekozen": "Seçiminiz: {label}.\nÖdəniş üçün {min} dəqiqəniz var ({bedrag} AZN):\n{link}",
        "fout": "Xəta baş verdi. Zəhmət olmasa yenidən cəhd edin.",
        "bevestigd": "Əla! Beh ödənişiniz alındı. {bedrijf}-dəki {label} tarixli görüşünüz təsdiqləndi. Görüşənədək!",
        "dag_labels": ["Bazar ertəsi","Çərşənbə axşamı","Çərşənbə","Cümə axşamı","Cümə","Şənbə","Bazar"],
        "maanden": ["","yanvar","fevral","mart","aprel","may","iyun","iyul","avqust","sentyabr","oktyabr","noyabr","dekabr"],
        "periode_label": "{a}-{b}. günlər",
    },
    "ru": {
        "kies_taal": "Выберите язык:",
        "welkom": "Добро пожаловать в {bedrijf}! Когда вы хотите прийти?",
        "kies_periode": "Выбрать период",
        "kies_dag": "Выберите день",
        "kies_dag_body": "Выберите день:",
        "kies_tijd": "Выберите время",
        "kies_tijd_body": "Выберите время:",
        "geen_dagen": "Нет свободных дней в этом периоде. Отправьте сообщение, чтобы выбрать снова.",
        "dag_vol": "Этот день занят. Отправьте сообщение, чтобы выбрать другой день.",
        "net_bezet": "К сожалению, это время только что заняли. Отправьте сообщение, чтобы выбрать снова.",
        "gekozen": "Вы выбрали: {label}.\nУ вас есть {min} минут для оплаты ({bedrag} AZN):\n{link}",
        "fout": "Что-то пошло не так. Попробуйте снова.",
        "bevestigd": "Отлично! Ваш задаток получен. Ваша запись на {label} в {bedrijf} подтверждена. До встречи!",
        "dag_labels": ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"],
        "maanden": ["","января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"],
        "periode_label": "Дни {a}-{b}",
    },
    "tr": {
        "kies_taal": "Bir dil seçin:",
        "welkom": "{bedrijf}'e hoş geldiniz! Ne zaman gelmek istersiniz?",
        "kies_periode": "Dönem seçin",
        "kies_dag": "Gün seçin",
        "kies_dag_body": "Gün seçin:",
        "kies_tijd": "Saat seçin",
        "kies_tijd_body": "Saat seçin:",
        "geen_dagen": "Bu dönemde boş gün yok. Tekrar seçmek için mesaj gönderin.",
        "dag_vol": "Bu gün dolu. Başka gün seçmek için mesaj gönderin.",
        "net_bezet": "Maalesef bu saat az önce doldu. Tekrar seçmek için mesaj gönderin.",
        "gekozen": "Seçiminiz: {label}.\nÖdeme için {min} dakikanız var ({bedrag} AZN):\n{link}",
        "fout": "Bir şeyler ters gitti. Lütfen tekrar deneyin.",
        "bevestigd": "Harika! Kaporanız alındı. {bedrijf} işletmesindeki {label} randevunuz kesinleşti. Görüşmek üzere!",
        "dag_labels": ["Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"],
        "maanden": ["","Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"],
        "periode_label": "{a}. gün - {b}. gün",
    },
    "en": {
        "kies_taal": "Choose a language:",
        "welkom": "Welcome to {bedrijf}! When would you like to come?",
        "kies_periode": "Choose period",
        "kies_dag": "Choose a day",
        "kies_dag_body": "Choose a day:",
        "kies_tijd": "Choose a time",
        "kies_tijd_body": "Choose a time:",
        "geen_dagen": "No free days in this period. Send a message to choose again.",
        "dag_vol": "This day is full. Send a message to choose another day.",
        "net_bezet": "Sorry, this time was just taken. Send a message to choose again.",
        "gekozen": "You chose: {label}.\nYou have {min} minutes to pay ({bedrag} AZN):\n{link}",
        "fout": "Something went wrong. Please try again.",
        "bevestigd": "Great! Your deposit has been received. Your appointment on {label} at {bedrijf} is confirmed. See you then!",
        "dag_labels": ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],
        "maanden": ["","January","February","March","April","May","June","July","August","September","October","November","December"],
        "periode_label": "Day {a} to {b}",
    },
}

def tr(taal, key, **kw):
    d = T.get(taal, T[STANDAARD_TAAL])
    tekst = d.get(key, T[STANDAARD_TAAL].get(key, key))
    return tekst.format(**kw) if kw else tekst

AANBETALING_BEDRAG = "5.00"
AANBETALING_OMSCHRIJVING = "Beh - Salon Test"

CALENDAR_ID = os.environ.get("CALENDAR_ID", "")
WERKDAG_START = 9
WERKDAG_EIND = 18
AFSPRAAK_DUUR = 30
DAGEN_VOORUIT = 60
BLOK_GROOTTE = 9
RESERVERING_MINUTEN = 15
TIJDZONE = "Asia/Baku"
TZ = ZoneInfo(TIJDZONE)

def _now():
    return datetime.now(TZ)

# ---- SISTEM ----
ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "azer12345")
PAYRIFF_SECRET = os.environ["PAYRIFF_SECRET"]
PAYRIFF_MERCHANT = os.environ.get("PAYRIFF_MERCHANT", "ES1097758")
BASE_URL = os.environ.get("BASE_URL", "https://afspraakbotazerbaijan-production.up.railway.app")
GOOGLE_KEY_JSON = os.environ["GOOGLE_KEY_JSON"]

app = Flask(__name__)
GRAPH = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
HEAD = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
PAYRIFF_HEAD = {"Authorization": PAYRIFF_SECRET, "Content-Type": "application/json"}

_creds = service_account.Credentials.from_service_account_info(
    json.loads(GOOGLE_KEY_JSON),
    scopes=["https://www.googleapis.com/auth/calendar"]
)
cal_service = build("calendar", "v3", credentials=_creds, cache_discovery=False)

PENDING_TAG = "[GOZLEMEDE]"
CONFIRMED_TAG = "[TESDIQLENDI]"

# ---------------- WhatsApp ----------------
def send_text(to, body):
    try:
        r = requests.post(GRAPH, headers=HEAD, json={
            "messaging_product": "whatsapp", "to": to,
            "type": "text", "text": {"body": body}
        }, timeout=10)
        if r.status_code >= 400:
            print(f"SEND_TEXT FAIL: {r.status_code} - {r.text[:200]}")
            return False
        print(f"✅ WhatsApp mesajı gönderildi: {to}")
        return True
    except Exception as e:
        print(f"SEND_TEXT HATA: {e}")
        return False

def send_list(to, header, body, button_text, rows, afbeelding=None):
    if afbeelding:
        try:
            requests.post(GRAPH, headers=HEAD, json={
                "messaging_product": "whatsapp", "to": to,
                "type": "image", "image": {"link": afbeelding}
            }, timeout=10)
            _time.sleep(0.2)
        except:
            pass
    
    interactive = {
        "type": "list",
        "header": {"type": "text", "text": (header or BEDRIJF_NAAM)[:60]},
        "body": {"text": (body or " ")[:1024]},
        "action": {
            "button": (button_text or "Seç")[:20],
            "sections": [{"title": "Seçimlər", "rows": rows[:10]}]
        }
    }
    try:
        r = requests.post(GRAPH, headers=HEAD, json={
            "messaging_product": "whatsapp", "to": to,
            "type": "interactive", "interactive": interactive
        }, timeout=10)
        if r.status_code >= 400:
            print(f"SEND_LIST FAIL: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"SEND_LIST HATA: {e}")

# ---------------- Takvim ----------------
def _events_between(start_dt, eind_dt):
    try:
        res = cal_service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_dt.isoformat(),
            timeMax=eind_dt.isoformat(),
            singleEvents=True, orderBy="startTime"
        ).execute()
        out = []
        for ev in res.get("items", []):
            s = ev["start"].get("dateTime")
            e = ev["end"].get("dateTime")
            if s and e:
                s = datetime.fromisoformat(s).astimezone(TZ)
                e = datetime.fromisoformat(e).astimezone(TZ)
                out.append((s, e))
        return out
    except Exception as e:
        print(f"_events_between HATA: {e}")
        return []

def bos_slotlar(d):
    dag_start = datetime.combine(d, dtime(WERKDAG_START, 0), tzinfo=TZ)
    dag_eind = datetime.combine(d, dtime(WERKDAG_EIND, 0), tzinfo=TZ)
    bezet = _events_between(dag_start, dag_eind)
    now = _now()
    slots = []
    t = dag_start
    while t + timedelta(minutes=AFSPRAAK_DUUR) <= dag_eind:
        slot_eind = t + timedelta(minutes=AFSPRAAK_DUUR)
        if t > now:
            overlaps = any(not (slot_eind <= b_s or t >= b_e) for (b_s, b_e) in bezet)
            if not overlaps:
                slots.append(t)
        t = slot_eind
    return slots

def bos_gunler_in_blok(blok_index, limit=9):
    result = []
    vandaag = _now().date()
    start_offset = 1 + blok_index * BLOK_GROOTTE
    for i in range(start_offset, start_offset + BLOK_GROOTTE):
        if i > DAGEN_VOORUIT:
            break
        d = vandaag + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        if bos_slotlar(d):
            result.append(d)
        if len(result) >= limit:
            break
    return result

def dag_label(d, taal=STANDAARD_TAAL):
    dl = T.get(taal, T[STANDAARD_TAAL])
    return f"{dl['dag_labels'][d.weekday()]} {d.day} {dl['maanden'][d.month]}"

def blok_label(blok_index, taal=STANDAARD_TAAL):
    start = 1 + blok_index * BLOK_GROOTTE
    eind = start + BLOK_GROOTTE - 1
    return tr(taal, "periode_label", a=start, b=eind)

def maak_pending(start_dt, klant_nummer):
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=TZ)
    eind_dt = start_dt + timedelta(minutes=AFSPRAAK_DUUR)
    event = {
        "summary": f"{PENDING_TAG} {klant_nummer}",
        "description": f"WhatsApp: {klant_nummer}. Odenis gozlenilir.",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIJDZONE},
        "end": {"dateTime": eind_dt.isoformat(), "timeZone": TIJDZONE},
    }
    created = cal_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    return created["id"]

def bevestig_event(event_id):
    try:
        ev = cal_service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
        ev["summary"] = ev["summary"].replace(PENDING_TAG, CONFIRMED_TAG)
        ev["description"] = ev.get("description", "").replace("Odenis gozlenilir.", "Odenildi.")
        cal_service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=ev).execute()
        return True
    except Exception as e:
        print(f"bevestig_event HATA: {e}")
        return False

def verwijder_event(event_id):
    try:
        cal_service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except Exception as e:
        print(f"verwijder_event HATA: {e}")

# ---------------- Temizleyici ----------------
def opschoon_loop():
    while True:
        try:
            now = _now()
            start = now - timedelta(days=1)
            eind = now + timedelta(days=DAGEN_VOORUIT + 1)
            res = cal_service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start.isoformat(),
                timeMax=eind.isoformat(),
                singleEvents=True, q=PENDING_TAG
            ).execute()
            for ev in res.get("items", []):
                if PENDING_TAG not in ev.get("summary", ""):
                    continue
                created = ev.get("created")
                if not created:
                    continue
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                leeftijd = (datetime.now(created_dt.tzinfo) - created_dt).total_seconds() / 60
                if leeftijd > RESERVERING_MINUTEN:
                    verwijder_event(ev["id"])
                    print(f"Temizlendi: {ev.get('summary')}")
        except Exception as e:
            print(f"opschoon_loop HATA: {e}")
        _time.sleep(300)

# ============================================================
# PAYRIFF ENTEGRASYONU - YENİDEN DÜZENLENDİ
# ============================================================

# Order'ları sakla (geçici bellek)
payriff_orders = {}

def create_payriff_payment(to, start_iso, label, event_id, taal="az"):
    """Payriff'te ödeme bağlantısı oluştur"""
    dil = {"az": "AZ", "ru": "RU", "en": "EN", "tr": "AZ"}.get(taal, "AZ")
    
    try:
        # Order oluştur
        payload = {
            "amount": float(AANBETALING_BEDRAG),
            "language": dil,
            "currency": "AZN",
            "description": f"{AANBETALING_OMSCHRIJVING} ({label})",
            "callbackUrl": f"{BASE_URL}/payriff-callback",
            "cardSave": False,
            "operation": "PURCHASE",
            "merchant": PAYRIFF_MERCHANT  # Merchant ID'yi ekleyelim
        }
        
        print(f"📤 PAYRIFF REQUEST: {json.dumps(payload)}")
        
        resp = requests.post(
            "https://api.payriff.com/api/v3/orders",
            headers=PAYRIFF_HEAD,
            json=payload,
            timeout=30
        )
        
        print(f"📥 PAYRIFF RESPONSE STATUS: {resp.status_code}")
        print(f"📥 PAYRIFF RESPONSE BODY: {resp.text[:500]}")
        
        if resp.status_code != 200:
            print(f"❌ Payriff order oluşturulamadı: {resp.status_code}")
            return None
            
        data = resp.json()
        
        # Response'u kontrol et
        if data.get("status") != "SUCCESS":
            print(f"❌ Payriff hatası: {data.get('message')}")
            return None
            
        payload_data = data.get("payload") or {}
        order_id = payload_data.get("orderId")
        payment_url = payload_data.get("paymentUrl")
        
        if order_id and payment_url:
            # Order'ı sakla
            payriff_orders[order_id] = {
                "whatsapp": to,
                "label": label,
                "event_id": event_id,
                "taal": taal,
                "created_at": datetime.now().isoformat()
            }
            print(f"✅ Payriff order oluşturuldu: {order_id}")
            print(f"🔗 Ödeme linki: {payment_url}")
            return payment_url
        else:
            print(f"❌ Payriff response'da orderId veya paymentUrl yok: {data}")
            return None
            
    except Exception as e:
        print(f"❌ create_payriff_payment HATA: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_payriff_order_status(order_id):
    """Payriff'ten order durumunu sorgula"""
    try:
        url = f"https://api.payriff.com/api/v3/orders/{order_id}"
        print(f"🔍 Checking order status: {url}")
        
        resp = requests.get(url, headers=PAYRIFF_HEAD, timeout=30)
        
        print(f"📊 Status check response: {resp.status_code}")
        print(f"📊 Status check body: {resp.text[:500]}")
        
        if resp.status_code != 200:
            return None
            
        data = resp.json()
        payload = data.get("payload") or {}
        
        return {
            "status": payload.get("paymentStatus"),
            "amount": payload.get("amount"),
            "currency": payload.get("currency"),
            "order_id": payload.get("orderId")
        }
    except Exception as e:
        print(f"❌ check_payriff_order_status HATA: {e}")
        return None


# ---------------- Webhook ----------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "fout", 403

    data = request.get_json(silent=True) or {}
    print(f">>> WEBHOOK: {json.dumps(data)[:500]}")
    
    try:
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        val = changes.get("value") or {}
        
        if "messages" not in val:
            return "ok", 200
            
        msg = val["messages"][0]
        frm = msg["from"]
        
        if msg["type"] == "text":
            rows = [{"id": f"taal_{t['code']}", "title": t["naam"]} for t in TALEN]
            send_list(frm, BEDRIJF_NAAM, tr(STANDAARD_TAAL, "kies_taal"), "Dil / Language", rows,
                      afbeelding=HEADER_AFBEELDING or None)
            return "ok", 200
            
        elif msg["type"] == "interactive":
            itype = msg["interactive"]["type"]
            reply_id = msg["interactive"]["list_reply"]["id"] if itype == "list_reply" else msg["interactive"].get("button_reply", {}).get("id", "")
            
            if reply_id.startswith("taal_"):
                taal = reply_id[5:]
                rows = []
                n_blokken = (DAGEN_VOORUIT + BLOK_GROOTTE - 1) // BLOK_GROOTTE
                for b in range(n_blokken):
                    rows.append({"id": f"blok_{b}_{taal}", "title": blok_label(b, taal)[:24]})
                send_list(frm, BEDRIJF_NAAM, tr(taal, "welkom", bedrijf=BEDRIJF_NAAM), tr(taal, "kies_periode"), rows)
                
            elif reply_id.startswith("blok_"):
                _, b_str, taal = reply_id.split("_", 2)
                b = int(b_str)
                dagen = bos_gunler_in_blok(b)
                if not dagen:
                    send_text(frm, tr(taal, "geen_dagen"))
                    return "ok", 200
                rows = [{"id": f"dag_{d.isoformat()}_{taal}", "title": dag_label(d, taal)[:24]} for d in dagen]
                send_list(frm, BEDRIJF_NAAM, tr(taal, "kies_dag_body"), tr(taal, "kies_dag"), rows)
                
            elif reply_id.startswith("dag_"):
                _, d_str, taal = reply_id.split("_", 2)
                d = datetime.fromisoformat(d_str).date()
                slots = bos_slotlar(d)
                if not slots:
                    send_text(frm, tr(taal, "dag_vol"))
                    return "ok", 200
                rows = [{"id": f"slot_{s.isoformat()}_{taal}", "title": s.strftime("%H:%M")} for s in slots[:10]]
                send_list(frm, dag_label(d, taal), tr(taal, "kies_tijd_body"), tr(taal, "kies_tijd"), rows)
                
            elif reply_id.startswith("slot_"):
                _, start_iso, taal = reply_id.split("_", 2)
                start_dt = datetime.fromisoformat(start_iso)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=TZ)
                if start_dt not in bos_slotlar(start_dt.date()):
                    send_text(frm, tr(taal, "net_bezet"))
                    return "ok", 200
                label = f"{dag_label(start_dt.date(), taal)} {start_dt.strftime('%H:%M')}"
                event_id = maak_pending(start_dt, frm)
                link = create_payriff_payment(frm, start_iso, label, event_id, taal)
                if link:
                    send_text(frm, tr(taal, "gekozen", label=label, min=RESERVERING_MINUTEN, bedrag=AANBETALING_BEDRAG, link=link))
                else:
                    verwijder_event(event_id)
                    send_text(frm, tr(taal, "fout"))
                    
    except Exception as e:
        print(f"WEBHOOK HATA: {e}")
        import traceback
        traceback.print_exc()
    
    return "ok", 200


# ---------------- Payriff Callback (YENİDEN DÜZENLENDİ) ----------------
@app.route("/payriff-callback", methods=["POST", "GET"])
def payriff_callback():
    """
    Payriff callback endpoint'i
    Payriff buraya ödeme sonucunu bildirir
    """
    print("=" * 60)
    print("🔔 PAYRIFF CALLBACK GELDİ!")
    print("=" * 60)
    
    # 1. Tüm veri kaynaklarını kontrol et
    data = {}
    
    # GET parametreleri
    if request.method == "GET":
        data = request.args.to_dict()
        print(f"📥 GET verileri: {data}")
    
    # POST verileri (JSON)
    if request.method == "POST":
        if request.is_json:
            data = request.get_json(silent=True) or {}
            print(f"📥 JSON verileri: {data}")
        else:
            # Form verileri
            data = request.form.to_dict()
            print(f"📥 Form verileri: {data}")
            
            # Raw body
            if not data:
                raw_data = request.data.decode('utf-8')
                print(f"📥 Raw body: {raw_data}")
                try:
                    if raw_data:
                        data = json.loads(raw_data)
                except:
                    pass
    
    # 2. Header'ları logla
    print(f"📋 Headers: {dict(request.headers)}")
    
    # 3. Order ID'yi bul (farklı formatlarda)
    order_id = None
    
    # Payriff'in gönderdiği formatları dene
    if isinstance(data, dict):
        # Payriff'in standart formatı
        if "payload" in data and isinstance(data["payload"], dict):
            order_id = data["payload"].get("orderId") or data["payload"].get("order_id")
        
        # Düz formatta
        if not order_id:
            order_id = data.get("orderId") or data.get("order_id") or data.get("id")
        
        # Eski format
        if not order_id:
            order_id = data.get("reference") or data.get("reference_id")
    
    # Query string'den dene
    if not order_id:
        order_id = request.args.get("orderId") or request.args.get("order_id")
    
    print(f"🔍 Bulunan Order ID: {order_id}")
    
    # 4. Eğer order ID yoksa, tüm anahtarları göster
    if not order_id:
        print("❌ Order ID bulunamadı!")
        print(f"📦 Tüm veri: {json.dumps(data, indent=2)}")
        return jsonify({"status": "error", "message": "Order ID not found"}), 200
    
    # 5. Order durumunu sorgula
    status_info = check_payriff_order_status(order_id)
    
    if not status_info:
        print(f"❌ Order {order_id} durumu sorgulanamadı")
        return jsonify({"status": "error", "message": "Cannot check order status"}), 200
    
    status = status_info.get("status")
    print(f"💰 ÖDEME STATUSU: {status}")
    
    # 6. Order bilgilerini al
    info = payriff_orders.get(order_id, {})
    to = info.get("whatsapp")
    label = info.get("label", "")
    event_id = info.get("event_id")
    taal = info.get("taal", "az")
    
    print(f"📋 Order bilgileri:")
    print(f"   - WhatsApp: {to}")
    print(f"   - Label: {label}")
    print(f"   - Event ID: {event_id}")
    print(f"   - Dil: {taal}")
    
    # 7. Duruma göre işlem yap
    if status == "PAID":
        print("✅ ÖDEME BAŞARILI!")
        
        if to and event_id:
            # Takvimi güncelle
            if bevestig_event(event_id):
                # WhatsApp mesajı gönder
                success_msg = tr(taal, "bevestigd", label=label, bedrijf=BEDRIJF_NAAM)
                send_text(to, success_msg)
                print(f"✅ WhatsApp onay mesajı gönderildi: {to}")
            else:
                print(f"❌ Event onaylanamadı: {event_id}")
        else:
            print(f"⚠️ Eksik bilgi: to={to}, event_id={event_id}")
        
        # Order'ı temizle
        payriff_orders.pop(order_id, None)
        print(f"🗑️ Order {order_id} temizlendi")
        
    elif status in ("DECLINED", "CANCELED", "EXPIRED", "FAILED"):
        print(f"❌ Ödeme başarısız: {status}")
        
        if event_id:
            verwijder_event(event_id)
            print(f"🗑️ Event {event_id} silindi")
        
        # Order'ı temizle
        payriff_orders.pop(order_id, None)
        print(f"🗑️ Order {order_id} temizlendi")
        
    else:
        print(f"ℹ️ Bilinmeyen durum: {status}")
    
    print("=" * 60)
    return jsonify({"status": "ok"}), 200


# ---------------- Başarılı Ödeme Sayfası ----------------
@app.route("/betaald", methods=["GET"])
def betaald():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ödəniş uğurlu!</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                background: rgba(255,255,255,0.95);
                padding: 50px 40px;
                border-radius: 24px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 90%;
                text-align: center;
            }
            .icon {
                font-size: 72px;
                margin-bottom: 20px;
            }
            h1 {
                color: #2d3748;
                font-size: 32px;
                margin-bottom: 10px;
            }
            p {
                color: #4a5568;
                font-size: 18px;
                line-height: 1.6;
                margin-bottom: 25px;
            }
            .btn {
                display: inline-block;
                background: #48bb78;
                color: white;
                padding: 14px 40px;
                border-radius: 50px;
                text-decoration: none;
                font-weight: 600;
                font-size: 16px;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: scale(1.05);
                box-shadow: 0 10px 20px rgba(72, 187, 120, 0.3);
            }
            .sub {
                color: #a0aec0;
                font-size: 14px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✅</div>
            <h1>Ödəniş uğurl
