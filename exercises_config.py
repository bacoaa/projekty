# ============================================================================
# exercises_config.py
# ----------------------------------------------------------------------------
# Ten plik NIE zawiera żadnej logiki aplikacji ani bazy danych - to czysta
# KONFIGURACJA Twojego planu treningowego. Dzięki temu, jeśli kiedyś zechcesz
# zmienić kolejność ćwiczeń, dodać nowe albo podmienić nazwę - grzebiesz
# TYLKO w tym pliku, a reszta aplikacji (app.py, database.py) się nie zmienia.
#
# STRUKTURA:
# WORKOUT_DAYS to lista trzech "dni treningowych" (PULL / PUSH / NOGI+BARKI).
# Każdy dzień to słownik z kluczami:
#   "day_key"   -> krótki, techniczny identyfikator dnia (używany w bazie danych)
#   "label"     -> ładna nazwa z emoji, wyświetlana na przycisku wyboru dnia
#   "title"     -> nagłówek wyświetlany na ekranie listy ćwiczeń danego dnia
#   "exercises" -> lista ćwiczeń przypisanych do tego dnia (patrz niżej)
#
# Każde ĆWICZENIE to słownik z kluczami:
#   "key"   -> unikalny, techniczny identyfikator ćwiczenia (używany jako
#              część kluczy widgetów Streamlit, żeby nic się nie gryzło)
#   "name"  -> pełna, czytelna nazwa ćwiczenia (to ona trafia też do bazy danych!)
#   "image" -> ścieżka do pliku ze zdjęciem (podmienisz ręcznie w folderze
#              placeholders/)
#   "note"  -> opcjonalna dodatkowa informacja pokazywana na ekranie aktywnego
#              ćwiczenia (np. że to część superserii); jeśli nie potrzeba - None
#
# UWAGA na "warianty" (np. Wersja A / Wersja B tego samego ćwiczenia):
# Zamiast pokazywać osobny przełącznik "radio", każdy wariant jest po prostu
# osobną pozycją na liście ćwiczeń (np. "... - wersja A" i "... - wersja B").
# To prostsze w architekturze wieloekranowej - po prostu wybierasz z listy
# tę wersję, którą faktycznie robisz danego dnia.
# ============================================================================


DEFAULT_SETS = 4
MAX_SETS = 5

# ---------------------------------------------------------------------------
# ZAKŁADKA / DZIEŃ 1: PULL (Plecy + Biceps)
# ---------------------------------------------------------------------------
PULL_EXERCISES = [
    {
        # Wariant A (szeroki chwyt) ściągania drążka wyciągu górnego.
        "key": "pull_01a",
        "name": "Ściąganie drążka wyciągu górnego – wersja A (szeroki chwyt)",
        "image": "placeholders/sciaganiegora.mp4",
        "note": None,
    },
    {
        # Wariant B (wąski chwyt) tego samego ćwiczenia - osobna pozycja na liście.
        "key": "pull_01b",
        "name": "Ściąganie drążka wyciągu górnego – wersja B (wąski chwyt)",
        "image": "placeholders/sciaganiegoraB.mp4",
        "note": None,
    },
    {
        "key": "pull_02",
        "name": "Uginanie ramion z hantlami na ławce skośnej (za tułowiem)",
        "image": "placeholders/uginaniehantel.mp4",
        "note": None,
    },
    {
        "key": "pull_03",
        "name": "Wiosłowanie z oparciem klatki o ławkę / maszyna",
        "image": "placeholders/wioslowanie.mp4",
        "note": None,
    },
    {
        "key": "pull_04",
        "name": "Przyciąganie jednorącz linki wyciągu dolnego (w oparciu)",
        "image": "placeholders/przyciaganie.mp4",
        "note": None,
    },
    {
        "key": "pull_05",
        "name": "Uginanie ramion na modlitewniku (gryf łamany)",
        "image": "placeholders/uginaniesztanga.mp4",
        "note": None,
    },
    {
        "key": "pull_06",
        "name": "\"Pies-Ptak\" (Bird-Dog) na macie",
        "image": "placeholders/birddog.mp4",
        "note": None,
    },
    {
        "key": "pull_07",
        "name": "Uginanie ramion z liną wyciągu dolnego (chwyt młotkowy)",
        "image": "placeholders/uginanielinka.mp4",
        "note": None,
    },
]

# ---------------------------------------------------------------------------
# ZAKŁADKA / DZIEŃ 2: PUSH (Klata + Triceps + Barki)
# ---------------------------------------------------------------------------
PUSH_EXERCISES = [
    {
        "key": "push_01a",
        "name": "Wyciskanie hantli – wersja A (skos dodatni)",
        "image": "placeholders/wyciskanieskos.mp4",
        "note": None,
    },
    {
        "key": "push_01b",
        "name": "Wyciskanie hantli – wersja B (ławka płaska)",
        "image": "placeholders/wyciskanieplasko.mp4",
        "note": None,
    },
    {
        "key": "push_02",
        "name": "Wyciskanie na maszynie siedząc (klatka)",
        "image": "placeholders/wyciskaniesiedzac.mp4",
        "note": None,
    },
    {
        "key": "push_03",
        "name": "Overhead Extension (wyciskanie linki wyciągu zza głowy)",
        "image": "placeholders/overhead.mp4",
        "note": None,
    },
    {
        # Pierwsza część superserii - "note" przypomina o drugiej części,
        # żeby user pamiętał, że robi je bez przerwy, jedno po drugim.
        "key": "push_04a",
        "name": "SUPERSERIA A) Ściąganie linki jednorącz na triceps",
        "image": "placeholders/sciaganielinkijednorocz.mp4",
        "note": "🔥 To pierwsza część superserii. Zaraz po tym, bez przerwy, "
                "zrób: „Wznosy bokiem na wyciągu (barki)”.",
    },
    {
        # Druga część tej samej superserii.
        "key": "push_04b",
        "name": "SUPERSERIA B) Wznosy bokiem na wyciągu (barki)",
        "image": "placeholders/barkwznosy.mp4",
        "note": "🔥 To druga część superserii, wykonywana od razu po: "
                "„Ściąganie linki jednorącz na triceps”.",
    },
    {
        "key": "push_05",
        "name": "Motylek (Pec Deck) / Rozpiętki",
        "image": "placeholders/rozpietki.mp4",
        "note": None,
    },
    {
        "key": "push_06",
        "name": "Dip Machine / Triceps Extension Machine",
        "image": "placeholders/tricepsmaszyna.mp4",
        "note": None,
    },
]

# ---------------------------------------------------------------------------
# ZAKŁADKA / DZIEŃ 3: NOGI + BARKI (kolejność zgodna z Twoim planem)
# ---------------------------------------------------------------------------
LEGS_EXERCISES = [
    {
        "key": "legs_01",
        "name": "Uginanie nóg na maszynie siedząc (tył uda)",
        "image": "placeholders/legs_01_leg_curl.jpg",
        "note": None,
    },
    {
        "key": "legs_02",
        "name": "Hack Squat (przysiad na maszynie)",
        "image": "placeholders/hacksquat.mp4",
        "note": None,
    },
    {
        "key": "legs_03",
        "name": "Wyciskanie hantli nad głowę siedząc (barki)",
        "image": "placeholders/overheadB.mp4",
        "note": None,
    },
    {
        "key": "legs_04",
        "name": "Wyprosty nóg na maszynie siedząc (przód uda)",
        "image": "placeholders/wyprostnog.mp4",
        "note": None,
    },
    {
        "key": "legs_05",
        "name": "Przywodziciele na maszynie (\"SUS Machine\")",
        "image": "placeholders/sus.mp4",
        "note": None,
    },
    {
        "key": "legs_06",
        "name": "Odwrotny Butterfly / Reverse Pec Deck (tył barku)",
        "image": "placeholders/odwrotnybutter.mp4",
        "note": None,
    },
]

# ---------------------------------------------------------------------------
# GŁÓWNA STRUKTURA UŻYWANA W app.py: lista trzech dni treningowych.
# Dzięki temu app.py może np. napisać:
#     for day in WORKOUT_DAYS:
#         st.button(day["label"])
# zamiast kopiować ten sam kod 3 razy dla PULL / PUSH / NOGI.
# ---------------------------------------------------------------------------
WORKOUT_DAYS = [
    {
        "day_key": "pull",
        "label": "🔙 PULL (Plecy + Biceps)",
        "title": "PULL – Plecy + Biceps",
        "exercises": PULL_EXERCISES,
    },
    {
        "day_key": "push",
        "label": "🔛 PUSH (Klata + Triceps + Barki)",
        "title": "PUSH – Klata + Triceps + Barki",
        "exercises": PUSH_EXERCISES,
    },
    {
        "day_key": "legs",
        "label": "🦵 NOGI + BARKI",
        "title": "NOGI + BARKI",
        "exercises": LEGS_EXERCISES,
    },
]


# ---------------------------------------------------------------------------
# FUNKCJE POMOCNICZE (używane głównie w widoku HISTORII, gdzie mamy tylko
# nazwę ćwiczenia zapisaną w bazie danych i musimy "odnaleźć" jej zdjęcie
# oraz do jakiego dnia należy).
# ---------------------------------------------------------------------------
def get_day_label(day_key):
    """
    Zamienia techniczny klucz dnia (np. "pull") na ładną nazwę z emoji
    (np. "🔙 PULL (Plecy + Biceps)"). Używane w historii, żeby ładnie
    wypisać "06.09 - 🔙 PULL (Plecy + Biceps)".
    Jeśli nie znajdzie dopasowania (nie powinno się zdarzyć), zwraca
    po prostu surowy klucz.
    """
    # Przeszukujemy listę wszystkich dni treningowych...
    for day in WORKOUT_DAYS:
        # ...i porównujemy techniczny klucz dnia z tym, czego szukamy.
        if day["day_key"] == day_key:
            # Znaleziono dopasowanie - zwracamy ładną etykietę.
            return day["label"]
    # Nic nie znaleziono - awaryjnie zwracamy surowy klucz, żeby appka
    # się nie wywaliła.
    return day_key


def find_exercise_by_name(exercise_name):
    """
    Szuka ćwiczenia o podanej pełnej nazwie we WSZYSTKICH dniach treningowych
    i zwraca jego pełną definicję (słownik z "key", "name", "image", "note").

    Używane na ekranie HISTORII: mamy tam tylko nazwę ćwiczenia zapisaną
    w bazie danych, a chcemy też pokazać jego zdjęcie - więc "odpytujemy"
    tę funkcję, żeby znaleźć pasujący wpis z konfiguracji.

    Zwraca None, jeśli nic nie znaleziono (np. ćwiczenie zostało kiedyś
    usunięte z konfiguracji, a w bazie nadal jest historia po nim).
    """
    # Przechodzimy po wszystkich dniach treningowych...
    for day in WORKOUT_DAYS:
        # ...a w każdym dniu po wszystkich jego ćwiczeniach...
        for ex in day["exercises"]:
            # ...i sprawdzamy, czy nazwa się zgadza.
            if ex["name"] == exercise_name:
                # Zgadza się - zwracamy cały słownik z definicją ćwiczenia.
                return ex
    # Żadne ćwiczenie nie pasowało - zwracamy None.
    return None
