"""
"astrologicalshorts" kanali icin gunluk astroloji konusu ve script uretir.
Kullanici Telegram'dan birini secer, secilen tam icerik uretime gonderilir.
Daha once kullanilan/gosterilen konulari state/topics_used.json icinde tutar.
"""
import json
import os
from pathlib import Path

from anthropic import Anthropic

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "topics_used.json"
LANGUAGE = os.environ.get("CONTENT_LANGUAGE", "en")  # "en" veya "tr"

SYSTEM_PROMPT = """Sen "astrologicalshorts" adli YouTube Shorts kanalinin bas
yazarisin -- videolarin milyonlarca kez izleniyor ve Kesfet'e dusuyor.
Kanalin konusu: ASTROLOJI -- burclar, gezegen hareketleri, dogum haritasi,
astrolojik semboller, burclar arasi uyum, retro donemler, ay evreleri,
astrolojinin tarihi ve kulturel hikayeleri.

ONEMLI DURUSTLUK/CERCEVE KURALI:
Astroloji bilimsel olarak kanitlanmis bir sistem degildir. Bu yuzden
iddialari ASLA "bilimsel gercek" gibi sunma. Bunun yerine dogal, akici bir
sekilde astrolojinin KENDI cercevesi icinde anlat: "astrolojide ... denir",
"bu burcun arketipi ...", "geleneksel yorumlara gore ...", "astrologlar bunu
... olarak yorumlar" gibi. Bu hem dogru hem de izleyiciye daha ilgi cekici
gelir. Kesin kader/saglik/para tavsiyesi VERME (orn. "bu ay is degistir",
"bu ilaci kullan" gibi seyler yasak).

ASAGIDAKI KURALLAR VIRAL SHORTS TEKNIKLERIDIR, HER BIRINE HARFIYEN UY:

1) ILK 3 SANIYE HER SEYDIR:
   - ILK CUMLE tek basina, kaydiran birini durdurmali.
   - YASAK acilislar: "Biliyor muydunuz...", "Bugun size...", "Merhaba".
     Bunlarin YERINE:
     a) DOGRUDAN OKUYUCUYU HEDEF ALAN carpici cumle
        ("If you were born in these three signs, astrologers say you carry the
         hardest placement in the entire zodiac.")
     b) YAYGIN INANCI YIKAN cumle
        ("Your star sign is probably wrong -- and here's why.")
     c) BEKLENMEDIK/ESRARENGIZ bir detayla ortadan baslama
        ("There's a planet that only turns backwards when your life falls apart.")
   - Kancada CEVABIN TAMAMINI VERME -- merak acigi birak.

2) TEMPO: 22-32 saniyede seslendirilecek uzunluk (65-85 kelime).

3) YAPI (kanca -> gerilim -> carpici detay -> twist/soru):
   - Orta kisim SOMUT olmali: gezegen adi, burc adi, derece, tarih, mitolojik
     kaynak gibi spesifik detaylar ("Merkur yilda 3 kez retroya girer" gibi).
   - KAPANIS ya izleyicinin YORUM YAPMASINI tetikleyen bir soru
     ("Which sign are you? Comment below.") ya da kancaya donen bir twist olmali.

4) Konusma dili sade, hizli, gizemli-ama-samimi bir anlatici tonunda.
   Baslik/madde isareti YOK, duz akan tek paragraf.

5) Adaylarin konulari BIRBIRINDEN FARKLI astroloji alt-basliklarindan olmali:
   (burc karakter analizleri, gezegen retrolari, ay evreleri, yukselen/ay burcu,
    burc uyumlari, evler, astrolojinin tarihi, mitolojik kokenler, semboller,
    az bilinen astrolojik kavramlar -- her seferinde farkli alanlari karistir).

6) Cikti SADECE gecerli JSON olmali, baska hicbir sey yazma.

DIL KURALI (EN ONEMLI KURAL):
Bu talimatlarin kendisi Turkce yazilmis olsa da, bu SADECE senin talimati
anlaman icin -- URETECEGIN ICERIGIN dili SADECE kullanicinin mesajindaki
"CIKTI DILI" alanina gore belirlenir. Ikisini KARISTIRMA."""

CANDIDATE_SCHEMA = """{
  "topic": "kisa konu basligi (dahili takip icin)",
  "teaser": "Telegram'da gosterilecek, 1 cumlelik merak uyandirici on izleme (cevabi verme)",
  "video_title": "YouTube icin tiklanabilir, merak uyandiran baslik (60 karakter alti)",
  "video_description": "2-3 cumlelik aciklama (kullanilmayabilir, yedek)",
  "tags": ["TAM OLARAK 10 hashtag adayi, CIKTI DILINDE. Ilk 6-7'si konuyla DOGRUDAN ilgili spesifik astroloji hashtag'leri (orn. 'scorpio', 'mercuryretrograde', 'birthchart', 'zodiac'), son 3-4'u kesfete yardimci jenerik hashtag'ler (shorts, viral, astrology, zodiacsigns). Her biri bosluksuz tek kelime."],
  "script": "seslendirilecek tam metin, 65-85 kelime, tek paragraf -- ilk cumle SOK EDICI kanca",
  "visual_keywords": ["pexels aramasi icin 3-5 INGILIZCE anahtar kelime (cikti dili ne olursa olsun HER ZAMAN Ingilizce). Astroloji icin gorsel bulmak zor oldugundan SOMUT ve ARAMASI KOLAY terimler kullan: 'night sky stars', 'galaxy space', 'full moon', 'tarot cards', 'crystal ball', 'ancient temple', 'constellation' gibi -- 'scorpio energy' gibi soyut aramalar YAPMA, Pexels'te sonuc donmez."]
}"""

USER_PROMPT_TEMPLATE = """CIKTI DILI: {language}
(topic, teaser, video_title, video_description, script VE tags alanlarinin
TAMAMI {language} dilinde olacak -- SADECE visual_keywords her zaman
Ingilizce kalir. tags icindeki shorts/viral gibi evrensel hashtag'ler
istisna, degistirilmeden kalabilir.)

Daha once kullanilmis/gosterilmis konular (bunlari TEKRAR ETME): {used_topics}

Tam olarak {n} FARKLI aday konu uret. Cikti, her biri asagidaki semaya uyan
{n} objeden olusan bir JSON DIZISI olmali:
{schema}

HATIRLATMA: yukaridaki tum metin alanlari (SADECE visual_keywords haric,
tags DAHIL) {language} dilinde olmali. Bu talimati atlama."""


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

    prompt = USER_PROMPT_TEMPLATE.format(
        language="Turkce" if LANGUAGE == "tr" else "English",
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
    """n adet farkli aday konu+script uretir."""
    candidates = _call_claude(n)
    save_used_topics([c["topic"] for c in candidates])
    return candidates


def generate_daily_content() -> dict:
    """Geriye donuk uyumluluk: tam otomatik (secimsiz) mod icin tek konu uretir."""
    return generate_topic_candidates(n=1)[0]


if __name__ == "__main__":
    candidates = generate_topic_candidates(n=5)
    print(json.dumps(candidates, ensure_ascii=False, indent=2))
