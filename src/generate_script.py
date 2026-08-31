"""
"astrologicalshorts" kanali icin gunluk astroloji konusu ve script uretir.
GERCEK gok verisi (sky_data.py) prompt'a dahil edilir, boylece retro/burc
gecisi gibi bilgiler uydurulmaz.
"""
import json
import os
from pathlib import Path

from anthropic import Anthropic

import sky_data

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "topics_used.json"
LANGUAGE = os.environ.get("CONTENT_LANGUAGE", "en")  # "en" veya "tr"

SYSTEM_PROMPT = """Sen "astrologicalshorts" adli YouTube Shorts kanalinin bas
yazarisin -- videolarin milyonlarca kez izleniyor ve Kesfet'e dusuyor.
Kanalin konusu: ASTROLOJI. Ozellikle GUNCEL gok olaylarini yorumlamak:
"bu hafta hangi gezegen retroda, hangi burclar etkilenir", "Ay su burcta,
bu ne anlama gelir", "su burcun bu donemde yasayabilecekleri" gibi.

GOK VERISI KURALI (COK ONEMLI):
Kullanicinin mesajinda sana BUGUNUN GERCEK GOK VERISI veriliyor. Tarih,
retro durumu, gezegen konumlari hakkinda konusurken SADECE o veriyi kullan.
Kendi hafizandan tarih/retro bilgisi UYDURMA -- yanlis bilgi verirsen kanalin
guvenilirligi zarar gorur. Veride olmayan bir sey hakkinda kesin tarih verme.

DURUSTLUK/CERCEVE KURALI:
Astroloji bilimsel olarak kanitlanmis degildir. Gezegen KONUMLARI gercektir
(astronomi), ama bunlarin insan hayatina etkisi astrolojik bir YORUMDUR.
Bu yuzden yorumlari astrolojinin kendi cercevesinde anlat: "astrolojide ...
denir", "astrologlar bunu ... olarak yorumlar", "geleneksel yorumlara gore".
Kesin kader/saglik/para/hukuk tavsiyesi VERME.

VIRAL SHORTS KURALLARI -- HARFIYEN UY:

1) ILK 3 SANIYE HER SEYDIR:
   - ILK CUMLE tek basina, kaydiran birini durdurmali.
   - YASAK acilislar: "Biliyor muydunuz...", "Bugun size...", "Merhaba".
     Bunlarin YERINE:
     a) OKUYUCUYU DOGRUDAN HEDEF ALAN carpici cumle
        ("If you're one of these three signs, this week hits you the hardest.")
     b) YAYGIN INANCI YIKAN cumle
        ("Mercury retrograde isn't what you think it is.")
     c) ACIL/ZAMANA BAGLI bir uyari
        ("Three planets are retrograde right now -- and one of them changes everything.")
   - Kancada CEVABIN TAMAMINI VERME -- merak acigi birak.

2) TEMPO: 22-32 saniyede seslendirilecek uzunluk (65-85 kelime).

3) YAPI (kanca -> gerilim -> somut detay -> twist/soru):
   - Orta kisim SOMUT olmali: gercek gezegen/burc/tarih bilgisi (verilen gok
     verisinden), spesifik derece veya tarih araligi.
   - KAPANIS ya yorum tetikleyen bir soru ("Which sign are you?") ya da
     kancaya donen bir twist olmali.

4) Konusma dili sade, hizli, gizemli-ama-samimi anlatici tonunda.
   Baslik/madde isareti YOK, duz akan tek paragraf.

5) 5 adayin konulari BIRBIRINDEN FARKLI olmali. Onerilen dagilim:
   - 2-3 tanesi GUNCEL gok verisine dayali (retro uyarisi, Ay evresi,
     gezegen gecisi, belirli burclar icin donem yorumu)
   - 2-3 tanesi zaman-bagimsiz astroloji konusu (burc arketipleri, yukselen
     burc, evler, astroloji tarihi, mitolojik kokenler, az bilinen kavramlar)

6) Cikti SADECE gecerli JSON olmali, baska hicbir sey yazma.

DIL KURALI (EN ONEMLI):
Bu talimatlar Turkce yazilmis olsa da bu SADECE senin anlaman icin --
URETECEGIN ICERIGIN dili SADECE kullanicinin "CIKTI DILI" alanina gore
belirlenir. Ikisini KARISTIRMA."""

CANDIDATE_SCHEMA = """{
  "topic": "kisa konu basligi (dahili takip icin)",
  "teaser": "Telegram'da gosterilecek, 1 cumlelik merak uyandirici on izleme (cevabi verme)",
  "video_title": "YouTube icin tiklanabilir, merak uyandiran baslik (60 karakter alti)",
  "video_description": "2-3 cumlelik aciklama (kullanilmayabilir, yedek)",
  "tags": ["TAM OLARAK 10 hashtag adayi, CIKTI DILINDE. Ilk 6-7'si konuyla ilgili spesifik astroloji hashtag'leri (orn. 'mercuryretrograde', 'fullmoon', 'virgoseason', 'birthchart'), son 3-4'u jenerik (shorts, viral, astrology, zodiac). Her biri bosluksuz tek kelime."],
  "script": "seslendirilecek tam metin, 65-85 kelime, tek paragraf -- ilk cumle SOK EDICI kanca",
  "visual_keywords": ["pexels aramasi icin 3-5 INGILIZCE anahtar kelime (HER ZAMAN Ingilizce). SOMUT ve ARAMASI KOLAY terimler kullan: 'night sky stars', 'galaxy space', 'full moon', 'tarot cards', 'crystal ball', 'ancient temple', 'constellation', 'planets space' gibi. 'scorpio energy' gibi soyut aramalar YAPMA, Pexels'te sonuc donmez."]
}"""

USER_PROMPT_TEMPLATE = """CIKTI DILI: {language}
(topic, teaser, video_title, video_description, script VE tags alanlarinin
TAMAMI {language} dilinde olacak -- SADECE visual_keywords her zaman
Ingilizce kalir. shorts/viral gibi evrensel hashtag'ler istisna.)

{sky_data}

Yukaridaki gok verisi GERCEK ve GUNCELDIR. Tarih/retro/gezegen konumu
bilgisi verirken SADECE bunu kullan, kendi hafizandan UYDURMA.

Daha once kullanilmis/gosterilmis konular (bunlari TEKRAR ETME): {used_topics}

Tam olarak {n} FARKLI aday konu uret. Cikti, her biri asagidaki semaya uyan
{n} objeden olusan bir JSON DIZISI olmali:
{schema}

HATIRLATMA: tum metin alanlari (visual_keywords haric, tags DAHIL)
{language} dilinde olmali."""


def load_used_topics() -> list:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("topics", [])
    return []


def save_used_topics(topics_to_add: list[str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    topics = load_used_topics()
    topics.extend(topics_to_add)
    topics = topics[-300:]
    STATE_FILE.write_text(json.dumps({"topics": topics}, ensure_ascii=False, indent=2), encoding="utf-8")


def _call_claude(n: int) -> list[dict]:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    used_topics = load_used_topics()

    snapshot = sky_data.get_sky_snapshot(language=LANGUAGE)
    sky_text = sky_data.format_for_prompt(snapshot)
    print("Kullanilan gok verisi:")
    print(sky_text)

    prompt = USER_PROMPT_TEMPLATE.format(
        language="Turkce" if LANGUAGE == "tr" else "English",
        sky_data=sky_text,
        used_topics=", ".join(used_topics[-60:]) if used_topics else "(yok, ilk video)",
        n=n,
        schema=CANDIDATE_SCHEMA,
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = "".join(block.text for block in response.content if block.type == "text").strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw_text)


def generate_topic_candidates(n: int = 5) -> list[dict]:
    candidates = _call_claude(n)
    save_used_topics([c["topic"] for c in candidates])
    return candidates


def generate_daily_content() -> dict:
    return generate_topic_candidates(n=1)[0]


if __name__ == "__main__":
    candidates = generate_topic_candidates(n=5)
    print(json.dumps(candidates, ensure_ascii=False, indent=2))
