"""
GERCEK gok verisi hesaplar (pyswisseph ile, dosya indirmeye gerek yok).
Claude'a "bugun gokte ne var" bilgisini SOMUT olarak verebilmek icin --
boylece retro tarihleri, burc gecisleri gibi seyleri UYDURMAK yerine
gercek veriye dayanarak yorumluyor.
"""
import datetime

import swisseph as swe

SIGNS_EN = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SIGNS_TR = [
    "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak",
    "Terazi", "Akrep", "Yay", "Oğlak", "Kova", "Balık",
]

PLANETS = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
    ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
]

MOON_PHASES = [
    (0, 22.5, "New Moon"),
    (22.5, 67.5, "Waxing Crescent"),
    (67.5, 112.5, "First Quarter"),
    (112.5, 157.5, "Waxing Gibbous"),
    (157.5, 202.5, "Full Moon"),
    (202.5, 247.5, "Waning Gibbous"),
    (247.5, 292.5, "Last Quarter"),
    (292.5, 337.5, "Waning Crescent"),
    (337.5, 360.1, "New Moon"),
]


def _julian_day(dt: datetime.datetime) -> float:
    return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)


def _sign_of(longitude: float, language: str = "en") -> str:
    index = int(longitude // 30) % 12
    return SIGNS_TR[index] if language == "tr" else SIGNS_EN[index]


def _moon_phase(sun_lon: float, moon_lon: float) -> str:
    angle = (moon_lon - sun_lon) % 360
    for low, high, name in MOON_PHASES:
        if low <= angle < high:
            return name
    return "Unknown"


def _find_retrograde_window(planet_id: int, start: datetime.datetime, days: int = 120) -> tuple | None:
    """Verilen gunden itibaren ileriye dogru tarayarak, gezegenin retro
    donemini (baslangic/bitis) bulur."""
    step_hours = 12
    steps = int(days * 24 / step_hours)
    prev_retro = None
    retro_start = None

    for i in range(steps):
        moment = start + datetime.timedelta(hours=i * step_hours)
        speed = swe.calc_ut(_julian_day(moment), planet_id)[0][3]
        is_retro = speed < 0

        if prev_retro is None:
            prev_retro = is_retro
            if is_retro:
                retro_start = start
            continue

        if is_retro and not prev_retro:
            retro_start = moment
        elif not is_retro and prev_retro and retro_start is not None:
            return (retro_start, moment)
        prev_retro = is_retro

    return None


def get_sky_snapshot(language: str = "en") -> dict:
    """Su ana ait gercek gok durumunu dondurur."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    jd = _julian_day(now)

    positions = {}
    retrogrades = []
    sun_lon = moon_lon = 0.0

    for name, pid in PLANETS:
        res = swe.calc_ut(jd, pid)[0]
        lon, speed = res[0], res[3]
        positions[name] = {
            "sign": _sign_of(lon, language),
            "degree_in_sign": round(lon % 30, 1),
            "retrograde": speed < 0,
        }
        if speed < 0 and name not in ("Sun", "Moon"):
            retrogrades.append(name)
        if name == "Sun":
            sun_lon = lon
        if name == "Moon":
            moon_lon = lon

    merc_window = _find_retrograde_window(swe.MERCURY, now)
    mercury_retro_info = None
    if merc_window:
        start, end = merc_window
        mercury_retro_info = {
            "currently_retrograde": positions["Mercury"]["retrograde"],
            "window_start": start.strftime("%Y-%m-%d"),
            "window_end": end.strftime("%Y-%m-%d"),
        }

    return {
        "date_utc": now.strftime("%Y-%m-%d"),
        "sun_sign": positions["Sun"]["sign"],
        "moon_sign": positions["Moon"]["sign"],
        "moon_phase": _moon_phase(sun_lon, moon_lon),
        "planets": positions,
        "retrograde_planets": retrogrades,
        "mercury_retrograde": mercury_retro_info,
    }


def format_for_prompt(snapshot: dict) -> str:
    """Gok verisini Claude'un rahat okuyabilecegi kisa bir metne cevirir."""
    lines = [
        f"BUGUNUN GERCEK GOK VERISI ({snapshot['date_utc']}, UTC):",
        f"- Gunes: {snapshot['sun_sign']} burcunda",
        f"- Ay: {snapshot['moon_sign']} burcunda, evre: {snapshot['moon_phase']}",
    ]

    if snapshot["retrograde_planets"]:
        lines.append(f"- SU AN RETRO olan gezegenler: {', '.join(snapshot['retrograde_planets'])}")
    else:
        lines.append("- Su an retro olan (Gunes/Ay disi) gezegen YOK")

    merc = snapshot.get("mercury_retrograde")
    if merc:
        durum = "EVET, su an retroda" if merc["currently_retrograde"] else "hayir, su an retro degil"
        lines.append(
            f"- Merkur retro durumu: {durum}. "
            f"Ilgili retro penceresi: {merc['window_start']} - {merc['window_end']}"
        )

    detay = ", ".join(
        f"{ad} {bilgi['sign']} {bilgi['degree_in_sign']}°{' (R)' if bilgi['retrograde'] else ''}"
        for ad, bilgi in snapshot["planets"].items()
    )
    lines.append(f"- Tum gezegen konumlari: {detay}")
    return "\n".join(lines)


if __name__ == "__main__":
    snap = get_sky_snapshot()
    print(format_for_prompt(snap))
