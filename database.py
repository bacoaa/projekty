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