from flask import Flask, request
import requests
import os
import json
import re
import threading
import time as _time
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============================================================
#  MUSTERI AYARLARI (config) - her yeni musteri icin burasi degisir
# ============================================================
BEDRIJF_NAAM = "Salon Test"
HEADER_AFBEELDING = ""  # ilk mesaj gorseli URL (bos "" = kapali)
BEGROETING = "Salon Test-e xos gelmisiniz!"

# ---- DILLER (Azerbaycan / Rus / Turk / Ingiliz) ----
STANDAARD_TAAL = "az"   # hicbir dil secilmezse varsayilan
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
WERKDAG_START = 9        # calisma baslangici (saat)
WERKDAG_EIND = 18        # calisma bitisi (saat)
AFSPRAAK_DUUR = 30       # randevu suresi (dakika)
DAGEN_VOORUIT = 60       # toplam kac gun ileriye bakilabilir
BLOK_GROOTTE = 9         # her aralik kac gun (9 gun)
RESERVERING_MINUTEN = 15 # odenmezse kac dk sonra silinsin
TIJDZONE = "Asia/Baku"   # Azerbaycan saati
TZ = ZoneInfo(TIJDZONE)

def _now():
    return datetime.now(TZ)
# ============================================================

# ---- SISTEM (Railway Variables) ----
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
    r = requests.post(GRAPH, headers=HEAD, json={
        "messaging_product": "whatsapp", "to": to,
        "type": "text", "text": {"body": body}
    })
    if r.status_code >= 400:
        print("SEND_TEXT FAIL:", r.status_code, r.text[:500], flush=True)


def send_image(to, link):
    """Ayri bir resim mesaji gonderir."""
    r = requests.post(GRAPH, headers=HEAD, json={
        "messaging_product": "whatsapp", "to": to,
        "type": "image", "image": {"link": link}
    })
    if r.status_code >= 400:
        print("SEND_IMAGE FAIL:", r.status_code, r.text[:500], flush=True)


def send_list(to, header, body, button_text, rows, afbeelding=None):
    # Resim varsa once ayri mesaj olarak gonder, kisa bir gecikmeyle siralamayi koru
    if afbeelding:
        send_image(to, afbeelding)
        _time.sleep(0.2)
    header_text = (header or BEDRIJF_NAAM or "Menu")[:60]
    interactive = {
        "type": "list",
        "header": {"type": "text", "text": header_text},
        "body": {"text": (body or " ")[:1024]},
        "action": {"button": (button_text or "Seç")[:20],
                   "sections": [{"title": "Seçimlər", "rows": rows[:10]}]}
    }
    r = requests.post(GRAPH, headers=HEAD, json={
        "messaging_product": "whatsapp", "to": to,
        "type": "interactive",
        "interactive": interactive
    })
    if r.status_code >= 400:
        print("SEND_LIST FAIL:", r.status_code, r.text[:500], flush=True)


# ---------------- Takvim okuma (dogrudan events.list) ----------------
def _events_between(start_dt, eind_dt):
    """Verilen aralikta takvimdeki tum etkinlikleri (start,end) TZ-aware olarak dondurur."""
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
        if not s or not e:
            continue
        s = datetime.fromisoformat(s).astimezone(TZ)
        e = datetime.fromisoformat(e).astimezone(TZ)
        out.append((s, e))
    return out


def bos_slotlar(d):
    """Bir gunun bos saat slotlarini (TZ-aware datetime listesi) dondurur."""
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
    """blok_index. araliktaki (9 gunluk) bos gunleri dondurur."""
    result = []
    vandaag = _now().date()
    start_offset = 1 + blok_index * BLOK_GROOTTE   # yarindan itibaren
    for i in range(start_offset, start_offset + BLOK_GROOTTE):
        if i > DAGEN_VOORUIT:
            break
        d = vandaag + timedelta(days=i)
        if d.weekday() >= 5:   # hafta sonu atla (gerekirse degistir)
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


# ---------------- Takvime yazma / silme ----------------
def maak_pending(start_dt, klant_nummer):
    """Slot secilince: takvime GOZLEMEDE kaydi at. Event id dondurur."""
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
    """Odeme gelince: GOZLEMEDE -> TESDIQLENDI.
    Idempotent: event zaten onaylanmissa (PENDING_TAG artik yoksa) False dondurur,
    boylece hem webhook hem de polling ayni odemeyi iki kere onaylayip
    musteriye iki kere mesaj gondermez."""
    try:
        ev = cal_service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
        summary = ev.get("summary", "")
        if PENDING_TAG not in summary:
            return False
        ev["summary"] = summary.replace(PENDING_TAG, CONFIRMED_TAG)
        ev["description"] = ev.get("description", "").replace("Odenis gozlenilir.", "Odenildi.")
        cal_service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=ev).execute()
        return True
    except Exception as e:
        print("bevestig_event HATA:", e)
        return False


def event_order_id_ekle(event_id, order_id):
    """Pending event'in description'ina order_id ekler, boylece polling dongusu
    bu event'in hangi Payriff siparisine ait oldugunu bulabilir."""
    try:
        ev = cal_service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
        desc = ev.get("description", "") or ""
        if "order:" not in desc:
            desc = f"{desc} | order:{order_id}"
            cal_service.events().patch(calendarId=CALENDAR_ID, eventId=event_id,
                                        body={"description": desc}).execute()
    except Exception as e:
        print("event_order_id_ekle HATA:", e)


def event_order_id_al(ev):
    desc = ev.get("description", "") or ""
    m = re.search(r"order:([\w-]+)", desc)
    return m.group(1) if m else None


def verwijder_event(event_id):
    try:
        cal_service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except Exception as e:
        print("verwijder_event HATA:", e)


# ---------------- Temizleyici: odenmemis GOZLEMEDE kayitlari sil ----------------
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
                    # Silmeden once son bir kez dogrudan Payriff'ten kontrol et:
                    # odeme aslinda yapilmis ama teyit (bevestig_event) herhangi bir
                    # sebeple gecikmisse, odenmis randevuyu yanlislikla silmeyelim.
                    order_id = event_order_id_al(ev)
                    if order_id:
                        status, meta = get_order_status(order_id)
                        if status == "PAID":
                            to = meta.get("whatsapp")
                            label = meta.get("label", "")
                            taal = meta.get("taal", "az")
                            if bevestig_event(ev["id"]) and to:
                                send_text(to, tr(taal, "bevestigd", label=label, bedrijf=BEDRIJF_NAAM))
                            continue
                    verwijder_event(ev["id"])
                    print("Temizlendi (odenmemis):", ev.get("summary"))
        except Exception as e:
            print("opschoon_loop HATA:", e)
        _time.sleep(300)  # her 5 dakika


# ---------------- Payriff (Azerbaycan yerel odeme) ----------------
# NOT: Siparisle ilgili bilgi (whatsapp numarasi, event_id, dil, label) artik
# process belleginde (dict) DEGIL, dogrudan Payriff'in "metadata" alaninda
# saklaniyor. Payriff bu alani musteriye gostermiyor ve callback/order
# sorgusunda aynen geri donduruyor. Boylece Railway'de birden fazla worker
# calissa da, uygulama yeniden baslasa da (redeploy/restart) bilgi kaybolmuyor
# -- cunku bellege hic yazilmiyor, her seferinde Payriff'ten okunuyor.
def create_payriff_payment(to, start_iso, label, event_id, taal="az"):
    """Basarili olursa (payment_url, order_id) tuple'i, basarisiz olursa (None, None) dondurur."""
    dil = {"az": "AZ", "ru": "RU", "en": "EN", "tr": "AZ"}.get(taal, "AZ")
    try:
        resp = requests.post("https://api.payriff.com/api/v3/orders",
                             headers=PAYRIFF_HEAD, json={
            "amount": float(AANBETALING_BEDRAG),
            "language": dil,
            "currency": "AZN",
            "description": f"{AANBETALING_OMSCHRIJVING} ({label})",
            "callbackUrl": f"{BASE_URL}/payriff-callback",
            "cardSave": False,
            "operation": "PURCHASE",
            "metadata": {
                "whatsapp": to,
                "label": label,
                "event_id": event_id,
                "taal": taal,
            },
        }, timeout=15)
        data = resp.json()
        print("PAYRIFF CREATE:", resp.status_code, json.dumps(data)[:500], flush=True)
        payload = data.get("payload") or {}
        payment_url = payload.get("paymentUrl")
        order_id = payload.get("orderId")
        return payment_url, order_id
    except Exception as e:
        print("PAYRIFF CREATE HATA:", e, flush=True)
        return None, None


def get_order_status(order_id):
    """Payriff'ten order durumunu ve metadata'yi sorgular. (status, metadata) dondurur."""
    try:
        r = requests.get(f"https://api.payriff.com/api/v3/orders/{order_id}",
                         headers=PAYRIFF_HEAD, timeout=15)
        payload = (r.json() or {}).get("payload") or {}
        return payload.get("paymentStatus"), (payload.get("metadata") or {})
    except Exception as e:
        print("PAYRIFF STATUS SORGU HATA:", order_id, e, flush=True)
        return None, {}


# ---------------- Odeme durumu icin polling dongusu ----------------
# Payriff'in callbackUrl'i bazi durumlarda (musteri odeme sonrasi tarayiciyi
# kapatirsa) hic tetiklenmeyebiliyor. Bu yuzden webhook'a ek olarak, bekleyen
# tum randevularin odeme durumunu duzenli araliklarla BIZ soruyoruz. Webhook
# calisirsa onay hizli gelir; calismazsa bu dongu en gec ~20 saniye icinde
# durumu yakalar. bevestig_event idempotent oldugu icin ikisi ayni anda
# tetiklense bile mesaj sadece bir kere gider.
def odeme_kontrol_loop():
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
                order_id = event_order_id_al(ev)
                if not order_id:
                    continue
                status, meta = get_order_status(order_id)
                if status == "PAID":
                    to = meta.get("whatsapp")
                    label = meta.get("label", "")
                    taal = meta.get("taal", "az")
                    if bevestig_event(ev["id"]) and to:
                        send_text(to, tr(taal, "bevestigd", label=label, bedrijf=BEDRIJF_NAAM))
                elif status in ("DECLINED", "CANCELED", "EXPIRED", "FAILED"):
                    verwijder_event(ev["id"])
        except Exception as e:
            print("odeme_kontrol_loop HATA:", e, flush=True)
        _time.sleep(20)  # her 20 saniyede bir kontrol et


# ---------------- WhatsApp webhook ----------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # --- GET: dogrulama ---
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "fout", 403

    # --- POST: gelen olay ---
    data = request.get_json(silent=True) or {}
    print(">>> WEBHOOK POST:", json.dumps(data)[:1500], flush=True)
    try:
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        val = changes.get("value") or {}

        # status/read makbuzu (messages yok, statuses var) -> sessizce gec
        if "messages" not in val:
            return "ok", 200

        msg = val["messages"][0]
        frm = msg["from"]

        if msg["type"] == "text":
            # 1. adim: dil sec
            rows = [{"id": f"taal_{t['code']}", "title": t["naam"]} for t in TALEN]
            send_list(frm, BEDRIJF_NAAM, tr(STANDAARD_TAAL, "kies_taal"), "Dil / Language", rows,
                      afbeelding=HEADER_AFBEELDING or None)
            return "ok", 200

        elif msg["type"] == "interactive":
            itype = msg["interactive"]["type"]
            if itype == "list_reply":
                reply_id = msg["interactive"]["list_reply"]["id"]
            else:
                reply_id = msg["interactive"].get("button_reply", {}).get("id", "")

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
                link, order_id = create_payriff_payment(frm, start_iso, label, event_id, taal)
                if link and order_id:
                    event_order_id_ekle(event_id, order_id)
                    send_text(frm, tr(taal, "gekozen", label=label, min=RESERVERING_MINUTEN, bedrag=AANBETALING_BEDRAG, link=link))
                else:
                    verwijder_event(event_id)
                    send_text(frm, tr(taal, "fout"))

    except Exception as e:
        print("HATA (webhook):", e, flush=True)
    return "ok", 200


# ---------------- Payriff callback ----------------
@app.route("/payriff-callback", methods=["POST", "GET"])
def payriff_callback():
    try:
        # Payriff callback'te orderId gonderir; biz de order durumunu sorgularız
        data = request.get_json(silent=True) or {}
        order_id = (data.get("payload") or {}).get("orderId") \
            or data.get("orderId") \
            or request.args.get("orderId") \
            or request.form.get("orderId")
        print(">>> PAYRIFF CALLBACK:", order_id, json.dumps(data)[:500], flush=True)
        if not order_id:
            return "ok", 200

        # Bu, webhook gelirse hizli yol saglar. Ama guvenceyi bu callback'e
        # degil, asagidaki odeme_kontrol_loop polling dongusune borcluyuz --
        # cunku Payriff'in callbackUrl'i her zaman garanti tetiklenmiyor
        # (bkz. yorum: odeme_kontrol_loop tanimi).
        status, meta = get_order_status(order_id)
        print(">>> PAYRIFF STATUS:", order_id, status, "META:", meta, flush=True)

        to = meta.get("whatsapp")
        label = meta.get("label", "")
        event_id = meta.get("event_id")
        taal = meta.get("taal", "az")

        if status == "PAID" and to and event_id:
            if bevestig_event(event_id):
                send_text(to, tr(taal, "bevestigd", label=label, bedrijf=BEDRIJF_NAAM))
        elif status in ("DECLINED", "CANCELED", "EXPIRED", "FAILED") and event_id:
            verwijder_event(event_id)
    except Exception as e:
        print("HATA (payriff-callback):", e, flush=True)
    return "ok", 200


@app.route("/betaald", methods=["GET"])
def betaald():
    return "Tesekkurler! Bu pencereni baglayib WhatsApp-a qayida bilersiniz.", 200


# temizleyici ve odeme-kontrol thread'lerini baslat
threading.Thread(target=opschoon_loop, daemon=True).start()
threading.Thread(target=odeme_kontrol_loop, daemon=True).start()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
