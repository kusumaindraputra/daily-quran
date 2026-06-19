"""
One-time script: Fetch full Quran (Arabic + English Sahih International)
from alquran.cloud free API, then generate a standalone-ayat pool.

Usage: .venv/bin/python fetch_quran.py
Outputs: quran_full.json, standalone_pool.json
"""

import json
import requests
import time

API_BASE = "https://api.alquran.cloud/v1"

# Arabic connecting words — ayats starting with these are likely
# mid-context and need the previous ayat to make sense.
ARABIC_CONNECTORS = [
    "و",      # وَ (and)
    "ف",      # فَ (then/so)
    "ث",      # ثُمَّ (then)
    "إ",      # إِذْ (when)
    "ل",      # لَمَّا (when)
]

# Max characters for the combined tweet (Arabic + English + reference).
# X Premium supports up to 25K chars, but for readability we keep posts
# concise. Ayahs whose combined text exceeds this are excluded from the pool.
MAX_COMBINED_CHARS = 600

# These surahs are entirely included regardless of connector check
# (short, mostly self-contained surahs from Juz 30 + Al-Fatihah)
FULLY_INCLUDED_SURAHS = {1, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90,
                          91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102,
                          103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114}

# Known standalone gems from longer surahs (surah:verse pairs)
# These are iconic ayats that are frequently quoted independently.
CURATED_STANDALONE = {
    # Al-Baqarah
    "2:255",   # Ayat Kursi
    "2:256",   # No compulsion in religion
    "2:286",   # Allah does not burden a soul
    # Ali 'Imran
    "3:26",    # Kingdom giver
    "3:103",   # Hold firmly to the rope of Allah
    "3:185",   # Every soul will taste death
    # An-Nisa
    "4:29",    # Do not kill yourselves
    "4:32",    # Do not wish for what Allah has favored
    "4:135",   # Be persistently standing firm in justice
    # Al-Ma'idah
    "5:8",     # Be just, that is nearer to righteousness
    "5:32",    # Whoever kills a soul
    # Al-An'am
    "6:59",    # Keys of the unseen
    "6:162",   # My prayer, my sacrifice
    # Al-A'raf
    "7:31",    # Eat and drink but be not excessive
    "7:180",   # The most beautiful names
    # Al-Anfal
    "8:30",    # They plan and Allah plans
    # At-Tawbah
    "9:40",    # Allah is with us
    "9:51",    # Never will we be struck except
    # Yunus
    "10:57",   # Instruction, healing, guidance, mercy
    # Hud
    "11:6",    # No creature on earth but Allah provides
    # Ar-Ra'd
    "13:11",   # Allah will not change the condition of a people
    "13:28",   # In the remembrance of Allah hearts find rest
    # Ibrahim
    "14:7",    # If you are grateful, I will increase you
    # Al-Hijr
    "15:49",   # Inform My servants that I am the Forgiving
    # An-Nahl
    "16:90",   # Allah orders justice and good conduct
    "16:97",   # Whoever does righteousness, male or female
    # Al-Isra
    "17:23",   # Worship none but Him, be good to parents
    "17:70",   # We have honored the children of Adam
    # Al-Kahf
    "18:46",   # Wealth and children are adornment
    "18:109",  # If the sea were ink
    # Maryam
    "19:96",   # The Most Merciful will appoint love
    # Taha
    "20:14",   # Indeed, I am Allah
    "20:25",   # My Lord, expand my chest
    "20:114",  # My Lord, increase me in knowledge
    # Al-Anbiya
    "21:35",   # Every soul will taste death
    "21:107",  # We have sent you as a mercy to the worlds
    # Al-Hajj
    "22:46",   # It is not the eyes that are blind
    # An-Nur
    "24:35",   # Light upon light (Ayat an-Nur)
    "24:40",   # Darkness in a vast deep sea
    # Al-Furqan
    "25:63",   # Servants of the Most Merciful
    # Ash-Shu'ara
    "26:78",   # He created me and He guides me
    # An-Naml
    "27:88",   # Mountains you think are solid
    # Al-Qasas
    "28:77",   # Do good as Allah has done good to you
    # Al-Ankabut
    "29:2",    # Do people think they will be left alone?
    "29:45",   # Prayer prohibits immorality
    "29:57",   # Every soul will taste death
    "29:69",   # Those who strive for Us
    # Ar-Rum
    "30:21",   # Created spouses for you
    "30:22",   # Diversity of languages and colors
    # Luqman
    "31:16",   # Mustard seed weight of deed
    "31:18",   # Do not turn your cheek in contempt
    # As-Sajdah
    "32:16",   # They forsake their beds
    # Al-Ahzab
    "33:35",   # Muslim men and Muslim women
    "33:56",   # Allah and His angels send blessings
    "33:70",   # Speak words of appropriate justice
    # Saba
    "34:13",   # Work, O family of David, in gratitude
    # Fatir
    "35:3",    # Is there any creator other than Allah?
    # Ya-Sin
    "36:82",   # Be, and it is
    # As-Saffat
    "37:180",  # Exalted is your Lord
    # Az-Zumar
    "39:9",    # Are those who know equal to those who do not?
    "39:53",   # Do not despair of the mercy of Allah
    # Ghafir
    "40:60",   # Call upon Me, I will respond to you
    # Fussilat
    "41:34",   # Repel evil with good
    "41:46",   # Whoever does righteousness — for his own soul
    # Ash-Shura
    "42:19",   # Allah is Subtle with His servants
    "42:30",   # Whatever misfortune strikes you
    # Az-Zukhruf
    "43:14",   # Indeed to our Lord we return
    # Ad-Dukhan
    "44:3",    # Blessed Night (Laylatul Qadr reference)
    # Al-Jathiyah
    "45:15",   # Whoever does a good deed
    # Al-Ahqaf
    "46:13",   # Those who say "Our Lord is Allah"
    # Muhammad
    "47:7",    # If you support Allah, He will support you
    "47:38",   # Allah is the Rich, you are the poor
    # Al-Fath
    "48:1",    # A clear victory
    # Al-Hujurat
    "49:10",   # Believers are but brothers
    "49:12",   # Avoid much suspicion
    "49:13",   # Made you peoples and tribes
    # Qaf
    "50:16",   # We are closer to him than his jugular vein
    "50:18",   # Not a word is uttered
    # Adh-Dhariyat
    "51:50",   # So flee to Allah
    "51:56",   # I created jinn and mankind only to worship Me
    # At-Tur
    "52:48",   # You are in Our eyes
    # An-Najm
    "53:38",   # No bearer of burdens bears another's
    "53:42",   # To your Lord is the final goal
    # Al-Qamar
    "54:49",   # Everything We created in due measure
    # Ar-Rahman
    "55:29",   # Every day He is in a matter
    "55:60",   # Is the reward for good anything but good?
    # Al-Waqi'ah
    "56:58",   # That which you emit
    # Al-Hadid
    "57:3",    # The First and the Last
    "57:4",    # He is with you wherever you are
    "57:20",   # Worldly life is play and amusement
    # Al-Mujadila
    "58:7",    # No secret counsel of three
    "58:11",   # Allah will raise those who believe
    # Al-Hashr
    "59:18",   # Let every soul look to what it has sent forth
    # Al-Mumtahina
    "60:8",    # Allah does not forbid you from being just
    # As-Saff
    "61:13",   # Help from Allah and a near victory
    # Al-Jumu'ah
    "62:10",   # Seek the bounty of Allah
    # Al-Munafiqun
    "63:11",   # Never will Allah delay a soul
    # At-Taghabun
    "64:11",   # No disaster strikes except by permission
    # At-Talaq
    "65:2",    # Whoever fears Allah, He makes a way out
    "65:3",    # Allah provides from where he does not expect
    # At-Tahrim
    "66:6",    # Protect yourselves and your families
    "66:8",    # O you who believe, repent sincerely
    # Al-Mulk
    "67:2",    # Created death and life to test you
    "67:13",   # Conceal your speech or reveal it
    # Al-Qalam
    "68:4",    # Indeed you are of great moral character
    # Al-Haqqah
    "69:48",   # A reminder for the righteous
    # Al-Ma'arij
    "70:5",    # Be patient with gracious patience
    "70:19",   # Man was created anxious
    # Nuh
    "71:10",   # Ask forgiveness of your Lord
    # Al-Jinn
    "72:16",   # If they remain on the right way
    # Al-Muzzammil
    "73:8",    # Remember the name of your Lord
    # Al-Muddaththir
    "74:4",    # Purify your garments
    # Al-Qiyamah
    "75:36",   # Does man think he will be left aimless?
    # Al-Insan
    "76:3",    # We guided him to the way
    # Al-Mursalat
    "77:15",   # Woe that Day to the deniers
    # An-Naba
    "78:40",   # Man will look at what his hands have sent
    # Abasa
    "80:24",   # Let man look at his food
    # At-Takwir
    "81:26",   # So where are you going?
    # Al-Infitar
    "82:6",    # What has deluded you about your Generous Lord?
    # Al-Mutaffifin
    "83:1",    # Woe to those who give less
    # Al-Inshiqaq
    "84:19",   # You will surely travel from stage to stage
    # Al-Buruj
    "85:14",   # He is the Forgiving, the Loving
    # At-Tariq
    "86:4",    # Every soul has a guardian over it
    # Al-A'la
    "87:14",   # He has succeeded who purifies himself
    # Al-Ghashiyah
    "88:17",   # Do they not look at the camels?
    # Al-Fajr
    "89:27",   # O reassured soul
    # Al-Balad
    "90:8",    # Have We not made for him two eyes?
    # Ash-Shams
    "91:7",    # By the soul and He who proportioned it
    "91:9",    # He has succeeded who purifies it
    # Al-Layl
    "92:4",    # Indeed your efforts are diverse
    # Ad-Duha
    "93:3",    # Your Lord has not forsaken you
    "93:7",    # He found you lost and guided you
    # Ash-Sharh
    "94:5",    # With hardship comes ease
    "94:6",    # Indeed, with hardship comes ease
    # At-Tin
    "95:8",    # Is Allah not the most just of judges?
    # Al-Alaq
    "96:1",    # Read in the name of your Lord
    # Al-Qadr
    "97:3",    # Night of Decree better than a thousand months
    # Al-Bayyinah
    "98:5",    # They were commanded only to worship Allah
    # Az-Zalzalah
    "99:7",    # Whoever does an atom's weight of good
    "99:8",    # Whoever does an atom's weight of evil
    # Al-Adiyat
    "100:6",   # Indeed mankind is ungrateful
    # Al-Qari'ah
    "101:6",   # He whose scales are heavy
    # At-Takathur
    "102:1",   # Competition in increase diverts you
    "102:8",   # You will surely be asked about pleasure
    # Al-Asr
    "103:2",   # Indeed mankind is in loss
    # Al-Humazah
    "104:3",   # He thinks his wealth will make him immortal
    # Al-Fil
    "105:4",   # Striking them with stones of baked clay
    # Quraysh
    "106:3",   # Let them worship the Lord of this House
    # Al-Ma'un
    "107:4",   # Woe to those who pray
    # Al-Kawthar
    "108:1",   # We have granted you Al-Kawthar
    # Al-Kafirun
    "109:6",   # To you your religion, to me mine
    # An-Nasr
    "110:3",   # Glorify the praise of your Lord, seek forgiveness
    # Al-Masad
    "111:5",   # Around her neck is a rope of palm fiber
    # Al-Ikhlas
    "112:1",   # Say: He is Allah, the One
    "112:2",   # Allah, the Eternal Refuge
    # Al-Falaq
    "113:5",   # From the evil of the envier when he envies
    # An-Nas
    "114:1",   # Say: I seek refuge in the Lord of mankind
}


def fetch_full_quran() -> list[dict]:
    """Fetch Arabic + English Yusuf Ali for all 114 surahs."""
    all_ayahs = []
    for surah_num in range(1, 115):
        url = f"{API_BASE}/surah/{surah_num}/editions/quran-uthmani,en.yusufali"
        resp = requests.get(url, timeout=30)
        data = resp.json()
        if data["status"] != "OK":
            print(f"  WARNING: Failed to fetch Surah {surah_num}")
            continue

        ar_ayahs = data["data"][0]["ayahs"]
        en_ayahs = data["data"][1]["ayahs"]

        for i, (ar, en) in enumerate(zip(ar_ayahs, en_ayahs)):
            all_ayahs.append({
                "surah": surah_num,
                "ayah": i + 1,
                "surah_name_en": ar.get("surah", {}).get("englishName", f"Surah {surah_num}"),
                "surah_name_ar": ar.get("surah", {}).get("name", ""),
                "ar_text": ar["text"],
                "en_text": en["text"],
                "key": f"{surah_num}:{i+1}",
            })

        print(f"  Surah {surah_num}: {len(ar_ayahs)} ayahs fetched")
        time.sleep(0.15)  # Be polite to the API

    print(f"\nTotal: {len(all_ayahs)} ayahs fetched")
    return all_ayahs


def starts_with_connector(ar_text: str) -> bool:
    """Check if Arabic text starts with a connecting particle."""
    if not ar_text:
        return False
    return ar_text[0] in ARABIC_CONNECTORS


def is_standalone(ayah: dict) -> tuple[bool, str]:
    """
    Determine if an ayah can stand alone for daily posting.
    Returns (is_standalone, reason).
    """
    key = ayah["key"]
    surah = ayah["surah"]
    ar_text = ayah["ar_text"]
    en_text = ayah["en_text"]

    # Curated standalone list always included regardless of length
    if key in CURATED_STANDALONE:
        return True, "curated"

    # Fully included surahs (Juz 30 + Al-Fatihah)
    if surah in FULLY_INCLUDED_SURAHS:
        return True, "juz30_or_fatihah"

    # Skip if combined text is too long for one post
    # +50 accounts for reference line and spacing
    combined_len = len(ar_text) + len(en_text) + 50
    if combined_len > MAX_COMBINED_CHARS:
        return False, "too_long"

    # Skip if starts with connector (mid-sentence continuation)
    if starts_with_connector(ar_text):
        return False, "connector_start"

    # Skip if English starts with lowercase (continuation)
    if en_text and en_text[0].islower():
        return False, "lowercase_start"

    return True, "length_pass"


def generate_standalone_pool(all_ayahs: list[dict]) -> list[dict]:
    """Filter ayahs to standalone pool and build curated list."""
    pool = []
    curated_count = 0
    juz30_count = 0
    length_count = 0
    skipped = {"too_long": 0, "connector_start": 0, "lowercase_start": 0}

    for ayah in all_ayahs:
        ok, reason = is_standalone(ayah)
        if ok:
            ayah["reason"] = reason
            pool.append(ayah)
            if reason == "curated":
                curated_count += 1
            elif reason == "juz30_or_fatihah":
                juz30_count += 1
            elif reason == "length_pass":
                length_count += 1
        else:
            skipped[reason] = skipped.get(reason, 0) + 1

    print(f"\nPool generated:")
    print(f"  Curated standalone:     {curated_count}")
    print(f"  Juz 30 + Al-Fatihah:    {juz30_count}")
    print(f"  Length/context pass:    {length_count}")
    print(f"  TOTAL POOL:             {len(pool)}")
    print(f"\nSkipped:")
    for reason, count in skipped.items():
        label = {
            "too_long": "Too long for one post",
            "connector_start": "Starts with connector word",
            "lowercase_start": "English starts lowercase (continuation)",
        }.get(reason, reason)
        print(f"  {label}: {count}")
    print(f"\n  Pool covers {len(pool)/len(all_ayahs)*100:.1f}% of Quran")
    print(f"  At 1/day: ~{len(pool)//365} years of daily content")

    return pool


def main():
    print("=" * 50)
    print(" Quran Daily — Fetch & Standalone Filter")
    print("=" * 50)

    # Fetch full Quran
    print("\n[1/3] Fetching full Quran from api.alquran.cloud...")
    all_ayahs = fetch_full_quran()

    # Save full dataset
    print("\n[2/3] Saving quran_full.json...")
    with open("quran_full.json", "w", encoding="utf-8") as f:
        json.dump(all_ayahs, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(all_ayahs)} ayahs to quran_full.json")

    # Generate standalone pool
    print("\n[3/3] Generating standalone pool...")
    pool = generate_standalone_pool(all_ayahs)

    with open("standalone_pool.json", "w", encoding="utf-8") as f:
        json.dump(pool, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(pool)} standalone ayahs to standalone_pool.json")

    print("\nDone! Ready for posting.")


if __name__ == "__main__":
    main()
