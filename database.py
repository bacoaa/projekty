# ============================================================================
# database.py
# ----------------------------------------------------------------------------
# Ten plik odpowiada WYŁĄCZNIE za rozmowę z bazą danych SQLite.
# Nic tu nie ma z "wyglądu" aplikacji (to jest w app.py) - tu jest tylko
# zapisywanie i odczytywanie danych. Taki podział to dobra praktyka:
# łatwiej się połapać, gdzie czego szukać.
#
# Baza danych to jeden plik "workout_log.db", który SQLite tworzy sam,
# na dysku, obok tego skryptu. Nie musisz instalować żadnego serwera bazy
# danych - SQLite to "baza danych w jednym pliku".
# ============================================================================

# Importujemy wbudowaną w Pythona bibliotekę do obsługi SQLite.
import sqlite3

# Importujemy "json" - potrzebny do zamiany Twoich niestandardowych planów
# treningowych (lista/słowniki Pythona) na zwykły tekst, który da się
# zapisać w jednej kolumnie SQLite, i z powrotem.
import json

# "os" - do sprawdzania/usuwania plików tymczasowych przy robieniu kopii
# zapasowej i przywracaniu bazy danych.
import os

# "shutil" - do bezpiecznego KOPIOWANIA plików (używane przy przywracaniu
# kopii zapasowej - podmieniamy plik bazy danych na nowy).
import shutil

# "tempfile" - do stworzenia TYMCZASOWEGO pliku, w którym testujemy
# przesłaną kopię zapasową, ZANIM nadpiszemy nią prawdziwą, używaną bazę
# (żeby zepsuty plik przypadkiem nie skasował Twoich prawdziwych danych).
import tempfile

# Importujemy narzędzia do pracy z datami i czasem (potrzebne np. do liczenia
# "3 tygodnie wstecz").
from datetime import datetime, timedelta

# "contextmanager" pozwala nam napisać własną funkcję, która działa
# z instrukcją "with ... as ...:" - dzięki temu połączenie z bazą zawsze
# zostanie poprawnie zamknięte, nawet gdyby coś się wysypało po drodze.
from contextlib import contextmanager

# Ścieżka do pliku bazy danych. Jedna stała, żeby nie powtarzać nazwy
# pliku w wielu miejscach kodu (łatwiej to potem zmienić).
DB_PATH = "workout_log.db"


# ----------------------------------------------------------------------------
# POŁĄCZENIE Z BAZĄ
# ----------------------------------------------------------------------------
@contextmanager
def get_connection():
    """
    Otwiera połączenie z bazą SQLite i "oddaje" je do użycia (yield),
    a kiedy blok "with" się skończy - AUTOMATYCZNIE zamyka połączenie,
    nawet jeśli w środku wyskoczy błąd. Dzięki temu nie musimy pamiętać
    o ręcznym conn.close() w każdej funkcji poniżej.
    """
    # Nawiązujemy połączenie z plikiem bazy danych (jeśli plik nie istnieje,
    # SQLite utworzy go automatycznie od zera).
    conn = sqlite3.connect(DB_PATH)

    # Ustawiamy "row_factory" na sqlite3.Row - dzięki temu wyniki zapytań
    # będziemy mogli odczytywać jak słownik, np. wiersz["weight"],
    # a nie tylko po numerze kolumny jak wiersz[2].
    conn.row_factory = sqlite3.Row

    # "try/finally" gwarantuje, że conn.close() wykona się ZAWSZE,
    # nawet jeśli kod korzystający z połączenia rzuci wyjątek.
    try:
        # "yield" oddaje połączenie do kodu, który wywołał "with get_connection() as conn:".
        yield conn
    finally:
        # Zamykamy połączenie - "sprzątamy po sobie".
        conn.close()


# ----------------------------------------------------------------------------
# TWORZENIE TABELI (uruchamiane raz, przy starcie aplikacji)
# ----------------------------------------------------------------------------
def init_db():
    """
    Tworzy tabelę 'workout_sets', jeśli jeszcze nie istnieje w bazie.
    Wywołujemy tę funkcję raz, na samym początku działania aplikacji (app.py).
    """
    # Otwieramy połączenie (kontekstowo - patrz funkcja get_connection wyżej).
    with get_connection() as conn:
        # "execute" wysyła zapytanie SQL do bazy danych.
        # "CREATE TABLE IF NOT EXISTS" oznacza: stwórz tabelę TYLKO jeśli
        # jeszcze jej nie ma - dzięki temu można wywoływać init_db() wielokrotnie
        # bez błędu "tabela już istnieje".
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workout_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unikalny numer wiersza, nadawany automatycznie
                date TEXT NOT NULL,                    -- data treningu, format "RRRR-MM-DD" (łatwo sortować)
                day_tab TEXT NOT NULL,                  -- klucz dnia treningowego, np. "pull", "push", "legs"
                exercise_name TEXT NOT NULL,            -- pełna nazwa ćwiczenia (tekst)
                set_number INTEGER NOT NULL,            -- numer serii w danym ćwiczeniu (1, 2, 3...)
                weight REAL NOT NULL,                   -- ciężar w kilogramach (liczba zmiennoprzecinkowa)
                reps INTEGER NOT NULL,                  -- liczba powtórzeń w tej serii
                created_at TEXT NOT NULL                -- dokładny znacznik czasu zapisu (do debugowania)
            )
            """
        )
        # "commit()" zatwierdza zmiany w bazie - bez tego CREATE TABLE
        # mogłoby się "nie zapisać" na stałe.
        conn.commit()

        # ---------------------------------------------------------------
        # NOWOŚĆ: druga, malutka tabela "app_state" - to prosty magazyn
        # "klucz -> wartość" na WSZYSTKO, co wcześniej żyło TYLKO w
        # st.session_state (czyli znikało po każdym przeładowaniu strony,
        # np. po powrocie z Spotify). Będziemy tu trzymać m.in. Twoje
        # własnoręcznie dodane plany treningowe i ćwiczenia.
        # ---------------------------------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,   -- nazwa zapisywanej rzeczy, np. "workout_days"
                value TEXT NOT NULL     -- jej zawartość, zapisana jako tekst JSON
            )
            """
        )
        conn.commit()

        # ---------------------------------------------------------------
        # NOWOŚĆ: trzecia tabela - "body_weight" (waga ciała w czasie).
        # Jeden wpis na dzień: jeśli zważysz się drugi raz tego samego
        # dnia, nowy pomiar NADPISUJE poprzedni (dzięki PRIMARY KEY na
        # kolumnie "date" - SQLite nie pozwoli mieć dwóch wierszy z tą
        # samą datą).
        # ---------------------------------------------------------------
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS body_weight (
                date TEXT PRIMARY KEY,  -- data pomiaru "RRRR-MM-DD" - jedna na dzień
                weight REAL NOT NULL,   -- waga w kg
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


# ----------------------------------------------------------------------------
# TRWAŁY MAGAZYN "KLUCZ -> WARTOŚĆ" (żeby dane przeżyły przeładowanie strony)
# ----------------------------------------------------------------------------
def save_app_state(key, value):
    """
    Zapisuje DOWOLNĄ strukturę danych Pythona (listę, słownik...) pod
    podaną nazwą (key), na trwałe, w bazie SQLite.

    "json.dumps(value, ensure_ascii=False)" zamienia np. listę słowników
    na jeden długi tekst w formacie JSON (ensure_ascii=False, żeby polskie
    znaki typu "ą", "ć" zapisywały się czytelnie, a nie jako "\\u0105").
    """
    with get_connection() as conn:
        tekst_json = json.dumps(value, ensure_ascii=False)
        # "INSERT OR REPLACE" wstawia nowy wiersz, A JEŚLI wiersz o takim
        # samym "key" już istnieje - po prostu go nadpisuje. Dzięki temu
        # nie musimy osobno sprawdzać "czy już istnieje" przed zapisem.
        conn.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
            (key, tekst_json),
        )
        conn.commit()


def load_app_state(key, default=None):
    """
    Odczytuje wcześniej zapisaną strukturę danych spod podanej nazwy (key).
    Jeśli nic tam jeszcze nie ma (np. pierwsze uruchomienie appki), zwraca
    wartość "default" zamiast wywalać błąd.
    """
    with get_connection() as conn:
        wiersz = conn.execute(
            "SELECT value FROM app_state WHERE key = ?", (key,)
        ).fetchone()
        if wiersz is None:
            return default
        # json.loads zamienia zapisany tekst z powrotem na listę/słownik Pythona.
        return json.loads(wiersz["value"])


# ----------------------------------------------------------------------------
# ZAPIS SERII DLA JEDNEGO ĆWICZENIA
# ----------------------------------------------------------------------------
def save_exercise_sets(date_str, day_tab, exercise_name, sets_data):
    """
    Zapisuje serie (ciężar + powtórzenia) dla jednego ćwiczenia, w jednym dniu.

    Parametry:
        date_str      - data w formacie "RRRR-MM-DD", np. "2026-09-06"
        day_tab       - klucz dnia treningowego, np. "pull"
        exercise_name - nazwa ćwiczenia, np. "Hack Squat (przysiad na maszynie)"
        sets_data     - lista słowników, np.:
                        [{"set_number": 1, "weight": 40.0, "reps": 10}, ...]

    Zasada działania: NAJPIERW kasujemy stare wpisy dla tej daty + tego
    ćwiczenia (gdyby user poprawiał wynik tego samego dnia), a POTEM
    wstawiamy nowe, świeże dane. Dzięki temu nie robią się duplikaty.

    Zwraca: liczbę faktycznie zapisanych serii (int).
    """
    # Otwieramy połączenie z bazą.
    with get_connection() as conn:
        # Usuwamy ewentualne wcześniejsze wpisy dla tej samej daty i ćwiczenia,
        # żeby ponowny zapis tego samego dnia nadpisywał, a nie duplikował dane.
        conn.execute(
            "DELETE FROM workout_sets WHERE date = ? AND exercise_name = ?",
            (date_str, exercise_name),
        )

        # Zapisujemy aktualny czas (do kolumny created_at) - przyda się,
        # gdybyśmy kiedyś chcieli sprawdzić "o której godzinie to wpisałem".
        now = datetime.now().isoformat()

        # Budujemy listę "krotek" (tuple) gotowych do wstawienia do bazy.
        # Warunek "if s['weight'] > 0 or s['reps'] > 0" odfiltrowuje puste
        # serie (np. gdy user zostawił jakieś pole na 0/0 i nic tam nie wpisał).
        rows = [
            (date_str, day_tab, exercise_name, s["set_number"], s["weight"], s["reps"], now)
            for s in sets_data
            if s["weight"] > 0 or s["reps"] > 0
        ]

        # Jeśli mamy cokolwiek do zapisania...
        if rows:
            # "executemany" wstawia od razu wiele wierszy w jednym poleceniu
            # (szybsze i czytelniejsze niż pętla z wieloma execute()).
            conn.executemany(
                """
                INSERT INTO workout_sets
                    (date, day_tab, exercise_name, set_number, weight, reps, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        # Zatwierdzamy zmiany (bez tego nic by się nie zapisało na trwałe).
        conn.commit()

        # Zwracamy liczbę zapisanych serii - app.py użyje tego do komunikatu
        # "Zapisano X serii".
        return len(rows)


def save_single_set(date_str, day_tab, exercise_name, set_number, weight, reps):
    """
    NOWOŚĆ: zapisuje JEDNĄ, konkretną serię od razu po jej wpisaniu -
    zamiast czekać, aż user skończy CAŁE ćwiczenie i kliknie duży przycisk
    na dole.

    DLACZEGO TO WAŻNE? Bo jeśli appka na telefonie przeładuje się w
    trakcie treningu (np. po powrocie z innej aplikacji), to WSZYSTKO, co
    jest tylko w polach na ekranie, a NIE jest jeszcze w bazie danych -
    znika bezpowrotnie. Zapisując każdą serię OD RAZU po jej zrobieniu,
    nic nie gubisz, nawet jeśli appka się przeładuje milisekundę później.

    W przeciwieństwie do save_exercise_sets() (która kasuje i na nowo
    wstawia WSZYSTKIE serie danego ćwiczenia na raz), ta funkcja rusza
    TYLKO wiersz o konkretnym numerze serii - inne, już zapisane serie
    tego ćwiczenia zostają nietknięte.

    Zwraca True, jeśli faktycznie coś zapisano (weight>0 lub reps>0),
    False jeśli pola były puste (0 i 0) - wtedy nic nie wstawiamy.
    """
    with get_connection() as conn:
        # Najpierw kasujemy STARY wpis TEJ KONKRETNEJ serii (jeśli istniał),
        # żeby ponowne zapisanie poprawionej wartości nadpisywało, a nie
        # duplikowało wiersz w bazie.
        conn.execute(
            """
            DELETE FROM workout_sets
            WHERE date = ? AND exercise_name = ? AND set_number = ?
            """,
            (date_str, exercise_name, set_number),
        )

        if weight > 0 or reps > 0:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO workout_sets
                    (date, day_tab, exercise_name, set_number, weight, reps, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date_str, day_tab, exercise_name, set_number, weight, reps, now),
            )
            conn.commit()
            return True

        conn.commit()
        return False


# ----------------------------------------------------------------------------
# HISTORIA TEKSTOWA (ostatnie N sesji, do wyświetlenia jako "co robiłem ostatnio")
# ----------------------------------------------------------------------------
def get_history(exercise_name, n_sessions=3, weeks_back=3):
    """
    Zwraca ostatnie 'n_sessions' treningów (maksymalnie 'weeks_back' tygodni
    wstecz) dla PODANEGO ćwiczenia. Wynik jest posortowany od najnowszego
    do najstarszego.

    Zwracany format (lista słowników):
    [
        {"date": "2026-09-06", "sets": [(1, 40.0, 10), (2, 42.5, 8)]},
        {"date": "2026-08-30", "sets": [(1, 40.0, 10)]},
        ...
    ]
    gdzie każda krotka w "sets" to (numer_serii, ciężar, powtórzenia).
    """
    # Liczymy datę graniczną - "dzisiaj minus X tygodni".
    # Wszystko starsze niż ta data nas nie interesuje w tym widoku.
    cutoff = (datetime.now() - timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")

    with get_connection() as conn:
        # Pobieramy UNIKALNE daty (DISTINCT), w których wykonano to ćwiczenie,
        # nie starsze niż "cutoff", posortowane malejąco (najnowsze pierwsze),
        # ograniczone do "n_sessions" wyników (LIMIT).
        date_rows = conn.execute(
            """
            SELECT DISTINCT date FROM workout_sets
            WHERE exercise_name = ? AND date >= ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (exercise_name, cutoff, n_sessions),
        ).fetchall()

        # Przygotowujemy pustą listę, do której będziemy dokładać wyniki.
        result = []

        # Dla każdej znalezionej daty pobieramy WSZYSTKIE serie z tego dnia.
        for row in date_rows:
            d = row["date"]  # wyciągamy samą wartość daty z wiersza
            set_rows = conn.execute(
                """
                SELECT set_number, weight, reps FROM workout_sets
                WHERE exercise_name = ? AND date = ?
                ORDER BY set_number ASC
                """,
                (exercise_name, d),
            ).fetchall()

            # Dodajemy do wyniku słownik z datą i listą serii (jako krotki).
            result.append(
                {
                    "date": d,
                    "sets": [(r["set_number"], r["weight"], r["reps"]) for r in set_rows],
                }
            )

        # Zwracamy gotową listę do wyświetlenia w app.py.
        return result


# ----------------------------------------------------------------------------
# SERIE ZAPISANE DLA KONKRETNEJ DATY (używane zarówno do prefillowania
# pól "dzisiaj", jak i do podglądu historycznego treningu z dowolnego dnia)
# ----------------------------------------------------------------------------
def get_sets_for_date(exercise_name, date_str):
    """
    Zwraca listę serii zapisanych dla danego ćwiczenia W KONKRETNYM DNIU.
    Format: [(numer_serii, ciężar, powtórzenia), ...]
    Używane w dwóch miejscach:
      1) żeby "podpowiedzieć" dzisiejsze pola, jeśli user już coś wpisał i
         odświeżył stronę,
      2) żeby pokazać szczegóły treningu z historii (dowolna przeszła data).
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT set_number, weight, reps FROM workout_sets
            WHERE exercise_name = ? AND date = ?
            ORDER BY set_number ASC
            """,
            (exercise_name, date_str),
        ).fetchall()

        # Zamieniamy wynik zapytania (obiekty sqlite3.Row) na zwykłe krotki
        # (numer_serii, ciężar, powtórzenia) - łatwiej się nimi operuje w app.py.
        return [(r["set_number"], r["weight"], r["reps"]) for r in rows]


# ----------------------------------------------------------------------------
# LISTA WSZYSTKICH ODBYTYCH SESJI (do ekranu "Historia" -> lista treningów)
# ----------------------------------------------------------------------------
def get_all_sessions():
    """
    Zwraca listę WSZYSTKICH odbytych sesji treningowych (unikalne pary
    data + dzień), posortowaną od najnowszej do najstarszej.

    Format: [{"date": "2026-09-06", "day_tab": "pull"}, {"date": "2026-09-04", "day_tab": "push"}, ...]

    Używane na ekranie "Historia", żeby pokazać listę typu:
    "06.09 - PULL", "04.09 - PUSH", itd.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT date, day_tab FROM workout_sets
            ORDER BY date DESC
            """
        ).fetchall()

        # Zamieniamy każdy wiersz na zwykły słownik Pythona.
        return [{"date": r["date"], "day_tab": r["day_tab"]} for r in rows]


# ----------------------------------------------------------------------------
# LISTA ĆWICZEŃ WYKONANYCH W DANYM DNIU (do ekranu "Podgląd treningu")
# ----------------------------------------------------------------------------
def get_exercises_for_session(date_str):
    """
    Zwraca listę nazw ćwiczeń wykonanych w danym dniu (dacie), w kolejności,
    w jakiej zostały pierwszy raz zapisane (czyli w kolejności wykonywania
    treningu) - dzięki sortowaniu po najmniejszym "id" dla danej nazwy.

    Zwraca zwykłą listę stringów, np.:
    ["Hack Squat (przysiad na maszynie)", "Wyciskanie hantli nad głowę siedząc (barki)", ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT exercise_name, MIN(id) AS first_id
            FROM workout_sets
            WHERE date = ?
            GROUP BY exercise_name
            ORDER BY first_id ASC
            """,
            (date_str,),
        ).fetchall()

        # Zwracamy tylko same nazwy ćwiczeń (bez "first_id", które służyło
        # jedynie do sortowania).
        return [r["exercise_name"] for r in rows]


# ----------------------------------------------------------------------------
# DANE DO WYKRESU POSTĘPÓW (maksymalny ciężar i "objętość" na dzień)
# ----------------------------------------------------------------------------
def get_progress_data(exercise_name):
    """
    Zwraca dane do wykresu liniowego postępu dla PODANEGO ćwiczenia,
    ze WSZYSTKICH zapisanych dotąd treningów (nie tylko 3 tygodnie),
    posortowane od najstarszej daty do najnowszej (tak, jak wykres
    powinien być czytany od lewej do prawej).

    Dla każdego dnia liczymy:
      - max_weight -> NAJWIĘKSZY ciężar użyty tego dnia w tym ćwiczeniu
                      (czyli "rekord dnia")
      - volume     -> SUMA (ciężar * powtórzenia) ze wszystkich serii tego dnia
                      (tzw. "objętość treningowa" - popularna miara progresu,
                      bo uwzględnia i ciężar, i liczbę powtórzeń)

    Zwraca listę słowników:
    [{"date": "2026-08-01", "max_weight": 40.0, "volume": 800.0}, ...]
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                date,
                MAX(weight) AS max_weight,
                SUM(weight * reps) AS volume
            FROM workout_sets
            WHERE exercise_name = ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (exercise_name,),
        ).fetchall()

        # Zamieniamy wynik SQL na listę zwykłych słowników Pythona -
        # łatwiej to potem przekazać do pandas / st.line_chart w app.py.
        return [
            {
                "date": r["date"],
                "max_weight": r["max_weight"],
                "volume": r["volume"],
            }
            for r in rows
        ]


def get_today_sets(exercise_name, date_str):
    """Zwraca wpisy zapisane już dziś dla danego ćwiczenia (do prefillowania pól)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT set_number, weight, reps FROM workout_sets
            WHERE exercise_name = ? AND date = ?
            ORDER BY set_number ASC
            """,
            (exercise_name, date_str),
        ).fetchall()
        return [(r["set_number"], r["weight"], r["reps"]) for r in rows]


# ----------------------------------------------------------------------------
# KOPIA ZAPASOWA BAZY DANYCH (eksport / import całego pliku .db)
# ----------------------------------------------------------------------------
# DLACZEGO TO POTRZEBNE? Streamlit Community Cloud NIE gwarantuje, że plik
# bazy danych przetrwa każdy restart/redeploy appki - w skrajnym przypadku
# cała historia treningów może zniknąć. Te dwie funkcje pozwalają Ci
# RĘCZNIE pobrać kopię całej bazy na swój telefon/komputer, a potem (gdyby
# dane zniknęły) wgrać ją z powrotem.
# ----------------------------------------------------------------------------
def eksportuj_baze_jako_bajty():
    """
    Odczytuje CAŁY plik bazy danych (workout_log.db) z dysku i zwraca go
    jako surowe bajty - dokładnie w takiej postaci, jakiej potrzebuje
    st.download_button() w app.py, żeby zaoferować Ci pobranie pliku.
    """
    # "rb" = "read binary" - czytamy plik jako surowe bajty, a nie tekst
    # (bazy danych SQLite to pliki binarne, nie da się ich otworzyć jako
    # zwykły tekst).
    with open(DB_PATH, "rb") as plik:
        return plik.read()


def waliduj_i_przywroc_baze(nowe_bajty):
    """
    Przyjmuje bajty PRZESŁANEGO przez Ciebie pliku (np. wcześniej pobranej
    kopii zapasowej) i - JEŚLI wygląda on na poprawną bazę danych tej
    aplikacji - podmienia nim obecny plik workout_log.db.

    WAŻNE zabezpieczenie: najpierw zapisujemy przesłane bajty do pliku
    TYMCZASOWEGO i sprawdzamy, czy da się z niego poprawnie odczytać
    tabelę "workout_sets". Dopiero jeśli test się powiedzie, nadpisujemy
    PRAWDZIWĄ bazę. Dzięki temu, jeśli przez pomyłkę wgrasz zepsuty albo
    zupełnie inny plik, Twoje obecne dane NIE ZOSTANĄ utracone.

    Zwraca krotkę (czy_sie_udalo: bool, komunikat: str).
    """
    # Tworzymy plik tymczasowy (sam go nie kasujemy automatycznie -
    # "delete=False" - bo chcemy go jeszcze otworzyć po zamknięciu bloku).
    tymczasowy_plik = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tymczasowy_plik.write(nowe_bajty)
    tymczasowy_plik.close()
    sciezka_tymczasowa = tymczasowy_plik.name

    try:
        # Próbujemy otworzyć przesłany plik jako bazę SQLite i wykonać na
        # nim najprostsze możliwe zapytanie - jeśli to nie jest poprawna
        # baza danych naszej aplikacji, to zapytanie rzuci wyjątkiem.
        testowe_polaczenie = sqlite3.connect(sciezka_tymczasowa)
        testowe_polaczenie.execute("SELECT COUNT(*) FROM workout_sets")
        testowe_polaczenie.close()
    except Exception as blad:
        # Plik NIE jest poprawną kopią zapasową - sprzątamy po sobie i
        # zwracamy informację o błędzie, NIE RUSZAJĄC prawdziwej bazy.
        os.remove(sciezka_tymczasowa)
        return False, f"To nie wygląda na poprawny plik kopii zapasowej ({blad})."

    # Plik przeszedł test - teraz bezpiecznie nadpisujemy nim prawdziwą
    # bazę danych aplikacji (shutil.copy nadpisuje plik docelowy, jeśli
    # już istnieje).
    shutil.copy(sciezka_tymczasowa, DB_PATH)
    os.remove(sciezka_tymczasowa)
    return True, "Przywrócono kopię zapasową! Odśwież stronę, żeby zobaczyć dane."


# ----------------------------------------------------------------------------
# WAGA CIAŁA W CZASIE
# ----------------------------------------------------------------------------
def zapisz_wage_ciala(date_str, waga_kg):
    """
    Zapisuje (albo NADPISUJE, jeśli dzisiaj już się ważyłeś) Twoją wagę
    ciała dla podanej daty. "INSERT OR REPLACE" działa tu tak samo jak
    w save_app_state() - jeśli wiersz z tą datą już istnieje, podmienia
    go nowym pomiarem, zamiast tworzyć duplikat.
    """
    with get_connection() as conn:
        teraz = datetime.now().isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO body_weight (date, weight, created_at) VALUES (?, ?, ?)",
            (date_str, waga_kg, teraz),
        )
        conn.commit()


def pobierz_historie_wagi_ciala():
    """
    Zwraca CAŁĄ historię pomiarów wagi ciała, od najstarszego do
    najnowszego pomiaru - gotowe do narysowania na wykresie liniowym.
    Format: [{"date": "2026-09-01", "weight": 82.4}, ...]
    """
    with get_connection() as conn:
        wiersze = conn.execute(
            "SELECT date, weight FROM body_weight ORDER BY date ASC"
        ).fetchall()
        return [{"date": w["date"], "weight": w["weight"]} for w in wiersze]


def pobierz_wage_na_dzien(date_str):
    """
    Zwraca wagę ciała zapisaną na KONKRETNY dzień, albo None, jeśli tego
    dnia jeszcze się nie ważyłeś. Używane do "podpowiedzenia" dzisiejszej
    wagi w polu input, jeśli już ją dziś wpisałeś.
    """
    with get_connection() as conn:
        wiersz = conn.execute(
            "SELECT weight FROM body_weight WHERE date = ?", (date_str,)
        ).fetchone()
        return wiersz["weight"] if wiersz is not None else None


# ----------------------------------------------------------------------------
# SZYBKIE STATYSTYKI (do wyświetlenia na Menu Głównym)
# ----------------------------------------------------------------------------
def pobierz_szybkie_statystyki():
    """
    Liczy kilka "podsumowujących" liczb z CAŁEJ historii treningów naraz -
    do pokazania jako duże, efektowne liczby na Menu Głównym.

    Zwraca słownik:
        {
            "liczba_treningow": int,   -> ile RÓŻNYCH dni treningowych odbyłeś
            "liczba_serii": int,       -> ile serii łącznie zapisałeś
            "laczna_objetosc": float,  -> suma (ciężar * powtórzenia) ze WSZYSTKICH serii
        }
    """
    with get_connection() as conn:
        # COUNT(DISTINCT date) liczy, ile RÓŻNYCH dat występuje w tabeli -
        # czyli ile osobnych dni treningowych odbyłeś (niezależnie od tego,
        # ile ćwiczeń/serii zrobiłeś danego dnia).
        liczba_treningow = conn.execute(
            "SELECT COUNT(DISTINCT date) AS ile FROM workout_sets"
        ).fetchone()["ile"]

        # Zwykłe COUNT(*) liczy WSZYSTKIE wiersze, czyli wszystkie
        # zapisane serie w historii appki.
        liczba_serii = conn.execute(
            "SELECT COUNT(*) AS ile FROM workout_sets"
        ).fetchone()["ile"]

        # SUM(weight * reps) liczy łączną "objętość treningową" (w kg) ze
        # WSZYSTKICH serii w historii - czyli ile kilogramów łącznie
        # "przerzuciłeś" od początku korzystania z appki.
        wynik_objetosci = conn.execute(
            "SELECT SUM(weight * reps) AS suma FROM workout_sets"
        ).fetchone()["suma"]
        # Jeśli baza jest pusta, SUM() zwraca SQL-owy NULL (czyli Python None)
        # zamiast 0 - zamieniamy to na zwykłe 0.0, żeby app.py nie musiało
        # się martwić o None przy wyświetlaniu liczby.
        laczna_objetosc = wynik_objetosci if wynik_objetosci is not None else 0.0

        return {
            "liczba_treningow": liczba_treningow,
            "liczba_serii": liczba_serii,
            "laczna_objetosc": laczna_objetosc,
        }


# ============================================================================
# SEKCJA "SUPER STATYSTYKI" - zaawansowany dashboard analityczny
# ============================================================================
def _poniedzialek_tygodnia(data_obj):
    """
    Pomocnicza funkcja: dla podanej daty zwraca datę PONIEDZIAŁKU tego
    samego tygodnia kalendarzowego. Używamy tego jako "klucza tygodnia"
    we WSZYSTKICH statystykach tygodniowych poniżej - dzięki temu dwie
    różne daty z tego samego tygodnia (np. wtorek i piątek) zawsze dadzą
    ten sam klucz, a różne tygodnie da się łatwo porównać / sprawdzić,
    czy są "kolejne" (różnica dokładnie 7 dni).

    "data_obj.weekday()" zwraca 0 dla poniedziałku, 1 dla wtorku, ..., 6
    dla niedzieli - więc odejmując tyle dni, zawsze "cofamy się" do
    najbliższego poniedziałku.
    """
    return data_obj - timedelta(days=data_obj.weekday())


def pobierz_tygodniowa_objetosc():
    """
    Zwraca łączną objętość treningową (ciężar * powtórzenia, zsumowane
    ze WSZYSTKICH ćwiczeń i serii) zgrupowaną PO TYGODNIU KALENDARZOWYM,
    od najstarszego do najnowszego tygodnia, w którym cokolwiek zapisałeś.

    Grupowanie po tygodniu (a nie po dniu) daje wyraźniejszy trend, nawet
    jeśli trenujesz nieregularnie w ciągu tygodnia.

    Format: [{"tydzien": "2026-08-25", "objetosc": 1234.5}, ...]
    (klucz "tydzien" to data PONIEDZIAŁKU danego tygodnia, w formacie
    "RRRR-MM-DD" - ten sam format co wszędzie indziej w bazie)
    """
    with get_connection() as conn:
        wiersze = conn.execute(
            "SELECT date, weight, reps FROM workout_sets ORDER BY date ASC"
        ).fetchall()

    objetosc_wg_tygodnia = {}
    for w in wiersze:
        data_obj = datetime.strptime(w["date"], "%Y-%m-%d")
        klucz = _poniedzialek_tygodnia(data_obj).strftime("%Y-%m-%d")
        objetosc_wg_tygodnia[klucz] = objetosc_wg_tygodnia.get(klucz, 0.0) + w["weight"] * w["reps"]

    return [
        {"tydzien": tydz, "objetosc": obj}
        for tydz, obj in sorted(objetosc_wg_tygodnia.items())
    ]


def pobierz_objetosc_wg_dnia_treningowego():
    """
    Zwraca łączną objętość treningową (od początku historii) zgrupowaną
    według TYPU dnia treningowego (klucz "day_tab", np. "pull"/"push"/
    "legs") - pokazuje, który typ treningu "waży" najwięcej w Twojej
    dotychczasowej historii.
    Format: {"pull": 12345.0, "push": 9876.0, "legs": 15000.0}
    """
    with get_connection() as conn:
        wiersze = conn.execute(
            "SELECT day_tab, SUM(weight * reps) AS suma FROM workout_sets GROUP BY day_tab"
        ).fetchall()
        return {w["day_tab"]: w["suma"] for w in wiersze}


def pobierz_rekordy_osobiste():
    """
    Dla KAŻDEGO ćwiczenia, jakie kiedykolwiek wykonałeś, znajduje jego
    najlepszy SZACOWANY 1RM (wzór Epleya) w całej historii, razem z datą,
    kiedy padł ten rekord, i dokładnym ciężarem/powtórzeniami, które go
    wygenerowały.

    Zwraca listę posortowaną malejąco wg 1RM (najmocniejsze ćwiczenie
    na górze):
    [{"cwiczenie": ..., "najlepszy_1rm": ..., "data": ..., "waga": ..., "powt": ...}, ...]
    """
    with get_connection() as conn:
        wiersze = conn.execute(
            "SELECT exercise_name, date, weight, reps FROM workout_sets"
        ).fetchall()

    najlepsze = {}  # exercise_name -> słownik z jego najlepszym wpisem
    for w in wiersze:
        if w["weight"] <= 0 or w["reps"] <= 0:
            continue
        rm = w["weight"] * (1 + w["reps"] / 30)
        obecny_rekord = najlepsze.get(w["exercise_name"])
        if obecny_rekord is None or rm > obecny_rekord["najlepszy_1rm"]:
            najlepsze[w["exercise_name"]] = {
                "Ćwiczenie": w["exercise_name"],
                "najlepszy_1rm": round(rm, 1),
                "Data": w["date"],
                "Ciężar (kg)": w["weight"],
                "Powt.": w["reps"],
            }

    lista = list(najlepsze.values())
    # Sortujemy malejąco po 1RM - najmocniejsze ćwiczenie na samej górze.
    lista.sort(key=lambda wpis: wpis["najlepszy_1rm"], reverse=True)

    # Zmieniamy nazwę techniczną "najlepszy_1rm" na ładną etykietę z
    # jednostką DOPIERO na końcu - dzięki temu sortowanie wyżej operowało
    # na czystej liczbie, a dopiero teraz "ubieramy" ją do wyświetlenia.
    for wpis in lista:
        wpis["Szacowany 1RM"] = f"{wpis.pop('najlepszy_1rm')} kg"

    return lista


def pobierz_info_o_passie():
    """
    Liczy Twoją "passę treningową" liczoną w TYGODNIACH KALENDARZOWYCH -
    czyli ile kolejnych tygodni z rzędu miałeś PRZYNAJMNIEJ JEDEN trening.
    To bardziej realistyczna miara niż "dni z rzędu", bo mało kto trenuje
    dosłownie codziennie.

    Zwraca: {"aktualna_passa": int, "najdluzsza_passa": int}
    (wartości w TYGODNIACH, nie dniach)
    """
    with get_connection() as conn:
        wiersze = conn.execute("SELECT DISTINCT date FROM workout_sets").fetchall()

    if not wiersze:
        return {"aktualna_passa": 0, "najdluzsza_passa": 0}

    # Zbiór UNIKALNYCH poniedziałków (jeden na każdy tydzień, w którym
    # cokolwiek zrobiłeś), posortowany chronologicznie.
    poniedzialki = sorted({
        _poniedzialek_tygodnia(datetime.strptime(w["date"], "%Y-%m-%d"))
        for w in wiersze
    })

    # --- Najdłuższa passa w CAŁEJ historii -----------------------------
    # Przechodzimy po kolejnych poniedziałkach: jeśli różnica między
    # kolejnymi wynosi DOKŁADNIE 7 dni, to są to "sąsiednie" tygodnie -
    # passa rośnie. W przeciwnym razie passa zaczyna się od nowa (= 1).
    najdluzsza = 1
    biezaca = 1
    for i in range(1, len(poniedzialki)):
        if (poniedzialki[i] - poniedzialki[i - 1]).days == 7:
            biezaca += 1
        else:
            biezaca = 1
        najdluzsza = max(najdluzsza, biezaca)

    # --- Aktualna passa (czy wciąż "żyje") -------------------------------
    # Sprawdzamy, czy ostatni zanotowany tydzień to tydzień BIEŻĄCY albo
    # POPRZEDNI (żeby nie zerować passy tylko dlatego, że ten tydzień
    # jeszcze się nie skończył, a user jeszcze dziś nie trenował).
    dzisiejszy_poniedzialek = _poniedzialek_tygodnia(datetime.now())
    ostatni_zanotowany = poniedzialki[-1]
    roznica_tygodni = (dzisiejszy_poniedzialek - ostatni_zanotowany).days // 7

    if roznica_tygodni <= 1:
        # Passa wciąż "żyje" - liczymy jej długość, cofając się od KOŃCA
        # listy poniedziałków, dopóki kolejne różnice to dokładnie 7 dni.
        aktualna = 1
        for i in range(len(poniedzialki) - 1, 0, -1):
            if (poniedzialki[i] - poniedzialki[i - 1]).days == 7:
                aktualna += 1
            else:
                break
    else:
        # Minął co najmniej jeden PEŁNY tydzień bez treningu - passa przerwana.
        aktualna = 0

    return {"aktualna_passa": aktualna, "najdluzsza_passa": najdluzsza}


def pobierz_korelacje_waga_objetosc():
    """
    Liczy WSPÓŁCZYNNIK KORELACJI PEARSONA między Twoją wagą ciała a
    tygodniową objętością treningową - czysta statystyka, bez żadnych
    zewnętrznych bibliotek (liczymy wzór ręcznie, bo appka nie ma numpy).

    Wartość "r" mieści się zawsze między -1 a +1:
        +1  -> idealna dodatnia korelacja (cięższe tygodnie = wyższa waga)
         0  -> brak liniowej zależności
        -1  -> idealna ujemna korelacja (cięższe tygodnie = niższa waga)

    Wymaga co najmniej 3 WSPÓLNYCH tygodni (czyli tygodni, w których masz
    ZARÓWNO zapisaną wagę ciała, JAK I trening) - przy mniejszej liczbie
    punktów korelacja nie ma sensu statystycznego, więc zwracamy None.

    Zwraca: {"r": float, "liczba_wspolnych_tygodni": int} albo None.
    """
    tygodniowa_objetosc = {
        wpis["tydzien"]: wpis["objetosc"] for wpis in pobierz_tygodniowa_objetosc()
    }

    historia_wagi = pobierz_historie_wagi_ciala()
    waga_wg_tygodnia = {}
    for wpis in historia_wagi:
        d = datetime.strptime(wpis["date"], "%Y-%m-%d")
        klucz = _poniedzialek_tygodnia(d).strftime("%Y-%m-%d")
        # Jeśli masz kilka pomiarów wagi w jednym tygodniu, bierzemy ich
        # ŚREDNIĄ (patrz obliczenie "srednia_waga_wg_tygodnia" niżej).
        waga_wg_tygodnia.setdefault(klucz, []).append(wpis["weight"])
    srednia_waga_wg_tygodnia = {
        tydz: sum(wagi) / len(wagi) for tydz, wagi in waga_wg_tygodnia.items()
    }

    # Interesują nas TYLKO tygodnie, które występują w OBU zbiorach danych.
    wspolne_tygodnie = sorted(
        set(tygodniowa_objetosc.keys()) & set(srednia_waga_wg_tygodnia.keys())
    )
    if len(wspolne_tygodnie) < 3:
        return None

    xs = [tygodniowa_objetosc[t] for t in wspolne_tygodnie]
    ys = [srednia_waga_wg_tygodnia[t] for t in wspolne_tygodnie]

    n = len(xs)
    srednia_x = sum(xs) / n
    srednia_y = sum(ys) / n

    # Wzór Pearsona: kowariancja podzielona przez iloczyn odchyleń
    # standardowych obu zmiennych.
    kowariancja = sum((x - srednia_x) * (y - srednia_y) for x, y in zip(xs, ys))
    odchylenie_x = sum((x - srednia_x) ** 2 for x in xs) ** 0.5
    odchylenie_y = sum((y - srednia_y) ** 2 for y in ys) ** 0.5

    if odchylenie_x == 0 or odchylenie_y == 0:
        # Brak jakiejkolwiek zmienności w jednej ze zmiennych (np. ta sama
        # waga ciała przez cały czas) - korelacja matematycznie nieokreślona.
        return None

    r = kowariancja / (odchylenie_x * odchylenie_y)
    return {"r": r, "liczba_wspolnych_tygodni": n}