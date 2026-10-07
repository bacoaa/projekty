# ============================================================================
# app.py - WERSJA CZYSTA BEZ ANIMACJI (Idealna na siłownię)
# ============================================================================

import streamlit as st
from datetime import datetime
import copy
import os

# streamlit.components.v1 pozwala wstawić WŁASNY kod HTML/JavaScript na
# stronę. Używamy tego TYLKO do stopera odpoczynku - czysty Python/Streamlit
# nie potrafi sam z siebie co sekundę odświeżać fragmentu ekranu bez pomocy
# usera, a JavaScript w przeglądarce potrafi to zrobić płynnie.
import streamlit.components.v1 as components

from database import (
    init_db, save_exercise_sets, save_single_set, get_history, get_today_sets,
    get_all_sessions, get_exercises_for_session, get_sets_for_date, get_progress_data,
    save_app_state, load_app_state,
    eksportuj_baze_jako_bajty, waliduj_i_przywroc_baze,
    zapisz_wage_ciala, pobierz_historie_wagi_ciala, pobierz_wage_na_dzien,
    pobierz_szybkie_statystyki,
)
from exercises_config import WORKOUT_DAYS, MAX_SETS

DEFAULT_SETS = 3
TODAY = datetime.now().strftime("%Y-%m-%d")

# Ile sekund ma domyślnie trwać stoper odpoczynku po zapisaniu serii.
SEKUNDY_ODPOCZYNKU = 90


def pokaz_stoper_odpoczynku(nonce, sekundy_startowe=SEKUNDY_ODPOCZYNKU):
    """
    Rysuje wizualny, SAMO-ODLICZAJĄCY się stoper odpoczynku w czystym
    JavaScript. "nonce" to liczba, którą zwiększamy przy KAŻDYM starcie
    stopera - dzięki temu treść komponentu jest za każdym razem inna, więc
    Streamlit tworzy go NA NOWO (a nie "dogrzewa" starego), czyli licznik
    zawsze zaczyna odliczać OD PEŁNEGO czasu, a nie kontynuuje poprzedni.
    """
    # Kolory stopera w stylu "skandynawskim" - stonowana terakota w trakcie
    # odpoczynku, szałwiowa zieleń, gdy czas minie (zamiast ostrej
    # czerwieni/zieleni ze starej wersji).
    kod_html = f"""
    <div id="stoper-kontener-{nonce}" style="
        text-align:center;
        font-family:'Inter', sans-serif;
        font-size:2rem;
        font-weight:600;
        padding:0.9rem;
        border-radius:14px;
        background: rgba(201, 123, 91, 0.12);
        color:#C97B5B;
        transition: all 0.4s ease;">
        ⏱️ Odpoczynek: <span id="stoper-liczba-{nonce}">{sekundy_startowe}</span> s
    </div>
    <script>
        let pozostaloSekund_{nonce} = {sekundy_startowe};
        const elementLiczby_{nonce} = document.getElementById("stoper-liczba-{nonce}");
        const elementKontenera_{nonce} = document.getElementById("stoper-kontener-{nonce}");

        // setInterval() uruchamia podaną funkcję co 1000 milisekund (1 sekundę).
        const idIntervalu_{nonce} = setInterval(function() {{
            pozostaloSekund_{nonce} = pozostaloSekund_{nonce} - 1;

            if (pozostaloSekund_{nonce} <= 0) {{
                elementKontenera_{nonce}.innerHTML = "💪 GOTOWE! Wracaj do ćwiczenia!";
                elementKontenera_{nonce}.style.background = "rgba(107, 143, 113, 0.15)";
                elementKontenera_{nonce}.style.color = "#6B8F71";
                clearInterval(idIntervalu_{nonce});
            }} else {{
                elementLiczby_{nonce}.innerText = pozostaloSekund_{nonce};
            }}
        }}, 1000);
    </script>
    """
    components.html(kod_html, height=90)

# ----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I STYLÓW CSS
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Dziennik Treningowy", page_icon="💪", layout="centered")

# ----------------------------------------------------------------------------
# PALETA KOLORÓW "SKANDYNAWSKA" - jedno miejsce, z którego czerpią WSZYSTKIE
# style w appce (CSS poniżej i kolory stopera dalej w pliku). Dzięki temu,
# jeśli kiedyś zechcesz zmienić np. główny kolor akcentu, podmieniasz go
# TYLKO tutaj, zamiast szukać po całym pliku.
# ----------------------------------------------------------------------------
KOLOR_TLO = "#FAF7F2"           # ciepła kremowa biel (jak papier/płótno)
KOLOR_TLO_KARTY = "#F0EBE3"     # lekko ciemniejszy beż - tła "kart" i pól
KOLOR_TEKST = "#2B2B2B"         # miękki węgiel zamiast czystej czerni
KOLOR_TEKST_PRZYGASZONY = "#8A8276"  # ciepły szary - podpisy, etykiety
KOLOR_AKCENT = "#6B8F71"        # szałwiowa zieleń - główny akcent (przyciski)
KOLOR_AKCENT_CIEMNY = "#56765C"  # ciemniejsza zieleń - hover/cień
KOLOR_AKCENT_DRUGI = "#C97B5B"  # stonowana terakota - stoper w trakcie, uwaga
KOLOR_SUKCES = "#6B8F71"        # zielony - "gotowe", sukces
KOLOR_OBRAMOWANIE = "#E2DDD4"   # cienkie, ciepłe, jasne obramowania

st.markdown(
    f"""
    <style>
        /* Wczytujemy nowoczesną, bezszeryfową czcionkę Google (Inter) -
           dużo "czystsza" i bardziej minimalistyczna niż domyślna systemowa,
           co dobrze pasuje do skandynawskiego, stonowanego stylu. */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, sans-serif;
        }}

        .block-container {{
            padding-top: 3.5rem !important;
            padding-bottom: 3rem;
            max-width: 600px;
        }}

        /* Nagłówki - lżejsza waga czcionki i więcej "oddechu" wygląda
           bardziej nowocześnie niż standardowe, grube pogrubienie. */
        h1, h2, h3 {{
            font-weight: 600 !important;
            color: {KOLOR_TEKST};
            letter-spacing: -0.02em;
        }}

        /* --- PRZYCISKI --------------------------------------------------- */
        div.stButton > button {{
            width: 100%;
            border-radius: 14px;
            font-weight: 600;
            border: 1.5px solid {KOLOR_OBRAMOWANIE};
            background-color: #FFFFFF;
            color: {KOLOR_TEKST};
            padding: 0.6rem 1rem;
            transition: all 0.15s ease;
            box-shadow: 0 1px 2px rgba(43, 43, 43, 0.04);
        }}
        div.stButton > button:hover {{
            border-color: {KOLOR_AKCENT};
            color: {KOLOR_AKCENT_CIEMNY};
            box-shadow: 0 2px 6px rgba(43, 43, 43, 0.08);
        }}
        div.stButton > button[kind="primary"] {{
            background-color: {KOLOR_AKCENT};
            color: white;
            border: none;
            box-shadow: 0 2px 8px rgba(107, 143, 113, 0.35);
        }}
        div.stButton > button[kind="primary"]:hover {{
            background-color: {KOLOR_AKCENT_CIEMNY};
        }}

        /* --- POLA LICZBOWE (ciężar / powtórzenia) ------------------------ */
        div[data-testid="stNumberInput"] input {{
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
            background-color: {KOLOR_TLO_KARTY};
            border: 1.5px solid {KOLOR_OBRAMOWANIE};
            color: {KOLOR_TEKST};
        }}

        /* --- KARTY / EXPANDERY -------------------------------------------
           Nadajemy im wygląd delikatnych "kart" - zaokrąglone rogi, cienka
           ramka, lekki cień - zamiast surowych, ostrych paneli. */
        div[data-testid="stExpander"] {{
            border-radius: 14px;
            border: 1.5px solid {KOLOR_OBRAMOWANIE};
            background-color: #FFFFFF;
        }}

        /* --- DROBNE PODPISY (st.caption) ---------------------------------- */
        [data-testid="stCaptionContainer"], .stCaption {{
            color: {KOLOR_TEKST_PRZYGASZONY} !important;
        }}

        /* --- LINIE PODZIAŁU (st.divider / ---) ---------------------------- */
        hr {{
            border-color: {KOLOR_OBRAMOWANIE} !important;
            margin: 0.8rem 0 !important;
        }}

        /* --- Natywne komunikaty Streamlit (info/warning/success) ---------
           Zostawiamy ich semantyczne kolory (niebieski/żółty/zielony), ale
           zaokrąglamy rogi i zdejmujemy ostrą ramkę, żeby pasowały do
           reszty, bardziej "miękkiego" stylu. */
        div[data-testid="stAlert"] {{
            border-radius: 12px;
            border: none;
        }}

        /* --- "Karta" podsumowania 1RM / historii -------------------------- */
        .skandy-karta {{
            background-color: {KOLOR_TLO_KARTY};
            border-radius: 12px;
            padding: 0.7rem 0.9rem;
            margin: 0.4rem 0 0.8rem 0;
            border-left: 3px solid {KOLOR_AKCENT};
            font-size: 0.85rem;
            color: {KOLOR_TEKST};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

# ----------------------------------------------------------------------------
# 2. NAWIGACJA I STAN APLIKACJI (Session State)
# ----------------------------------------------------------------------------

# --- 2a. PLANY TRENINGOWE: wczytujemy je z bazy danych, a NIE zawsze od
#         zera. To naprawia najpoważniejszy błąd starej wersji: Twoje
#         własnoręcznie dodane/edytowane plany i ćwiczenia żyły WYŁĄCZNIE
#         w pamięci sesji (session_state) i znikały bezpowrotnie przy
#         każdym przeładowaniu strony (np. po powrocie z innej aplikacji).
#         Teraz: jeśli w bazie jest już zapisany komplet planów - używamy
#         go. Jeśli nie (pierwsze uruchomienie appki w ogóle) - budujemy
#         domyślny plan z exercises_config.py i OD RAZU zapisujemy go do
#         bazy, żeby był tam na przyszłość.
if "workout_days" not in st.session_state:
    zapisane_plany = load_app_state("workout_days", default=None)

    if zapisane_plany is not None:
        # W bazie jest już komplet planów (domyślnych i/lub Twoich własnych)
        # - używamy go dokładnie takiego, jaki ostatnio zostawiłeś.
        st.session_state.workout_days = zapisane_plany
    else:
        # Baza jeszcze pusta - budujemy plan startowy z konfiguracji.
        initial_days = copy.deepcopy(WORKOUT_DAYS)
        for d in initial_days:
            d["is_default"] = True
            for ex in d["exercises"]:
                ex["is_default"] = True
        st.session_state.workout_days = initial_days
        # Zapisujemy go od razu do bazy, żeby przy następnym uruchomieniu
        # (nawet po awarii/restarcie appki) nie trzeba było zaczynać od zera.
        save_app_state("workout_days", st.session_state.workout_days)


def persist_workout_days():
    """
    Woła się PO KAŻDEJ zmianie planów/ćwiczeń (dodanie, edycja, usunięcie),
    żeby ta zmiana natychmiast trafiła do bazy danych, a nie została tylko
    w pamięci sesji. Bez tego wywołania Twoje zmiany znowu ginęłyby po
    przeładowaniu strony.
    """
    save_app_state("workout_days", st.session_state.workout_days)


# --- 2b. PRZYWRACANIE EKRANU PO PRZEŁADOWANIU STRONY -------------------------
# Kiedy przeglądarka na telefonie "usypia" kartę (np. przełączasz się na
# Spotify) i potem ją przeładowuje, Streamlit traci CAŁY session_state i
# zaczyna nową sesję od zera - domyślnie appka wracała wtedy zawsze do
# Menu Głównego, nawet jeśli byłeś w środku wpisywania serii.
#
# Rozwiązanie: oprócz session_state, zapisujemy "gdzie jesteśmy" TAKŻE w
# adresie URL (tzw. "query params") - a URL, w przeciwieństwie do
# session_state, PRZEŻYWA przeładowanie strony. Dzięki temu, jeśli
# session_state jest świeże (czyli to naprawdę nowa sesja), próbujemy
# odtworzyć poprzedni ekran na podstawie tego, co jest zapisane w URL.
if "page" not in st.session_state:
    zapisana_strona = st.query_params.get("page", "menu")
    zapisany_dzien_klucz = st.query_params.get("day")
    zapisane_cwiczenie_klucz = st.query_params.get("ex")

    # Bezpieczna wartość domyślna - gdyby coś dalej nie pasowało.
    st.session_state.page = "menu"

    if zapisana_strona in ("select_day", "history"):
        # Te dwa ekrany nie wymagają żadnych dodatkowych danych do odtworzenia.
        st.session_state.page = zapisana_strona

    elif zapisana_strona == "exercise_list" and zapisany_dzien_klucz:
        # Szukamy w aktualnie wczytanych planach dnia o zapamiętanym kluczu.
        dzien = next(
            (d for d in st.session_state.workout_days if d["day_key"] == zapisany_dzien_klucz),
            None,
        )
        if dzien:
            st.session_state.current_day_key = zapisany_dzien_klucz
            st.session_state.page = "exercise_list"

    elif zapisana_strona == "active_exercise" and zapisany_dzien_klucz and zapisane_cwiczenie_klucz:
        dzien = next(
            (d for d in st.session_state.workout_days if d["day_key"] == zapisany_dzien_klucz),
            None,
        )
        if dzien:
            cwiczenie = next(
                (e for e in dzien["exercises"] if e["key"] == zapisane_cwiczenie_klucz),
                None,
            )
            if cwiczenie:
                st.session_state.current_day_key = zapisany_dzien_klucz
                st.session_state.current_exercise = cwiczenie
                st.session_state.page = "active_exercise"
    # W każdym innym przypadku (np. puste query params przy pierwszej
    # wizycie) zostajemy przy bezpiecznej wartości domyślnej "menu".

if "edit_mode_plans" not in st.session_state:
    st.session_state.edit_mode_plans = False

# --- NOWOŚĆ: stan wizualnego stopera odpoczynku ------------------------------
# Czy stoper ma być w ogóle narysowany w tym przebiegu skryptu.
if "stoper_widoczny" not in st.session_state:
    st.session_state.stoper_widoczny = False

# "nonce" zwiększamy za każdym razem, gdy user zapisze serię - wymusza to
# narysowanie stopera OD NOWA (patrz komentarz przy pokaz_stoper_odpoczynku()).
if "stoper_nonce" not in st.session_state:
    st.session_state.stoper_nonce = 0

if "edit_mode_ex" not in st.session_state:
    st.session_state.edit_mode_ex = False

if "is_admin_unlocked" not in st.session_state:
    st.session_state.is_admin_unlocked = False

if "editing_plan_key" not in st.session_state:
    st.session_state.editing_plan_key = None

if "editing_ex_key" not in st.session_state:
    st.session_state.editing_ex_key = None


def go_to_menu():
    st.session_state.page = "menu"
    # Czyścimy URL z parametrów - menu nie potrzebuje żadnego kontekstu.
    st.query_params.clear()


def go_to_workout_day_selection():
    st.session_state.page = "select_day"
    st.query_params.clear()
    st.query_params["page"] = "select_day"


def go_to_exercise_list(day_data):
    st.session_state.current_day_key = day_data["day_key"]
    st.session_state.page = "exercise_list"
    # Zapisujemy w URL, na jakim jesteśmy ekranie i którego dnia dotyczy -
    # dzięki temu przeładowanie strony (np. po powrocie z innej appki)
    # przywróci Cię DOKŁADNIE tutaj, a nie do Menu Głównego.
    st.query_params.clear()
    st.query_params["page"] = "exercise_list"
    st.query_params["day"] = day_data["day_key"]


def go_to_exercise(exercise_data):
    st.session_state.current_exercise = exercise_data
    st.session_state.page = "active_exercise"
    # Tu dodatkowo zapisujemy KLUCZ konkretnego ćwiczenia, żeby po
    # przeładowaniu appka wiedziała, które dokładnie ćwiczenie odtworzyć.
    st.query_params.clear()
    st.query_params["page"] = "active_exercise"
    st.query_params["day"] = st.session_state.current_day_key
    st.query_params["ex"] = exercise_data["key"]


def go_to_history():
    st.session_state.page = "history"
    st.query_params.clear()
    st.query_params["page"] = "history"


# ----------------------------------------------------------------------------
# 3. WIDOKI APLIKACJI
# ----------------------------------------------------------------------------

# --- EKRAN 0: MENU GŁÓWNE ---
if st.session_state.page == "menu":
    st.title("💪 Twój Dziennik")
    st.write("Wybierz, co robimy dzisiaj:")

    if st.button("🔥 NOWY TRENING", type="primary", key="menu_new_workout"):
        go_to_workout_day_selection()
        st.rerun()

    if st.button("📚 HISTORIA I WYKRESY", key="menu_history"):
        go_to_history()
        st.rerun()

    # ------------------------------------------------------------------
    # NOWOŚĆ: SZYBKIE STATYSTYKI
    # ------------------------------------------------------------------
    # Trzy duże liczby podsumowujące CAŁĄ dotychczasową historię - "na
    # pierwszy rzut oka" widzisz swój postęp, bez wchodzenia w Historię.
    # st.metric() to wbudowany w Streamlit widget do pokazywania właśnie
    # takich "kafelkowych" liczb (duża cyfra + mały podpis pod spodem).
    st.write("")  # odrobina odstępu
    statystyki = pobierz_szybkie_statystyki()

    if statystyki["liczba_treningow"] > 0:
        kol_stat1, kol_stat2, kol_stat3 = st.columns(3)
        kol_stat1.metric("Treningi", statystyki["liczba_treningow"])
        kol_stat2.metric("Serie", statystyki["liczba_serii"])
        # ":,.0f" formatuje liczbę z separatorem tysięcy i bez miejsc po
        # przecinku (np. 12450 -> "12,450") - czytelniej dla dużych liczb.
        kol_stat3.metric("Objętość", f"{statystyki['laczna_objetosc']:,.0f} kg")

    # ------------------------------------------------------------------
    # NOWOŚĆ: WAGA CIAŁA W CZASIE
    # ------------------------------------------------------------------
    with st.expander("⚖️ Waga ciała"):
        st.caption("Zważ się i zapisz wynik - zobaczysz, jak zmienia się Twoja waga na przestrzeni czasu.")

        # Jeśli dzisiaj już się ważyłeś, podpowiadamy tę wartość w polu,
        # zamiast zaczynać zawsze od zera.
        dzisiejsza_waga = pobierz_wage_na_dzien(TODAY)
        wartosc_startowa = dzisiejsza_waga if dzisiejsza_waga is not None else 70.0

        kol_waga_input, kol_waga_btn = st.columns([2, 1])
        nowa_waga = kol_waga_input.number_input(
            "Twoja waga dzisiaj (kg)",
            min_value=0.0,
            max_value=300.0,
            step=0.1,
            value=wartosc_startowa,
            key="input_waga_ciala",
            label_visibility="collapsed",
        )
        if kol_waga_btn.button("💾 Zapisz wagę", key="zapisz_wage_btn"):
            zapisz_wage_ciala(TODAY, nowa_waga)
            st.toast(f"Zapisano wagę: {nowa_waga:g} kg", icon="⚖️")
            st.rerun()

        # Wykres - tylko jeśli mamy co najmniej 2 pomiary (jeden punkt nie
        # tworzy sensownej linii).
        historia_wagi = pobierz_historie_wagi_ciala()
        if len(historia_wagi) > 1:
            dane_wykresu = {wpis["date"]: wpis["weight"] for wpis in historia_wagi}
            st.line_chart(dane_wykresu)
        elif len(historia_wagi) == 1:
            st.caption("Zapisz wagę jeszcze raz innego dnia, żeby zobaczyć wykres zmian.")

    # ------------------------------------------------------------------
    # NOWOŚĆ: KOPIA ZAPASOWA BAZY DANYCH
    # ------------------------------------------------------------------
    # Streamlit Community Cloud NIE gwarantuje, że plik bazy danych
    # przetrwa każdy restart appki - dlatego dajemy Ci prosty sposób na
    # ręczne zabezpieczenie CAŁEJ historii treningów: pobranie jej jako
    # jeden plik, i w razie czego - wgranie z powrotem.
    # Używamy st.expander(), żeby ta sekcja była domyślnie ZWINIĘTA i nie
    # rzucała się w oczy na co dzień.
    with st.expander("⚙️ Kopia zapasowa danych"):
        st.caption(
            "Streamlit czasem resetuje zapisane dane przy aktualizacjach "
            "appki. Pobieraj kopię zapasową raz na jakiś czas (np. co "
            "tydzień), żeby nigdy nie stracić historii treningów."
        )

        # --- POBIERANIE KOPII ZAPASOWEJ -----------------------------------
        # st.download_button potrzebuje gotowych BAJTÓW pliku - dostaje je
        # z funkcji eksportuj_baze_jako_bajty() z database.py.
        dane_do_pobrania = eksportuj_baze_jako_bajty()
        st.download_button(
            label="📥 Pobierz kopię zapasową",
            data=dane_do_pobrania,
            file_name=f"kopia_zapasowa_{TODAY}.db",
            mime="application/octet-stream",
            key="pobierz_kopie_btn",
        )

        st.markdown("---")

        # --- PRZYWRACANIE Z KOPII ZAPASOWEJ --------------------------------
        st.caption("Chcesz przywrócić wcześniej pobraną kopię? Wgraj ją tutaj:")
        wgrany_plik = st.file_uploader(
            "Wybierz plik kopii zapasowej (.db)",
            type=["db"],
            key="wgraj_kopie_uploader",
            label_visibility="collapsed",
        )
        if wgrany_plik is not None:
            # Pokazujemy czerwone ostrzeżenie PRZED wykonaniem akcji -
            # przywrócenie kopii NADPISUJE całą obecną bazę danych.
            st.warning(
                "⚠️ To NADPISZE całą obecną bazę danych wgranym plikiem. "
                "Tej operacji nie da się cofnąć."
            )
            if st.button("♻️ Tak, przywróć tę kopię zapasową", key="przywroc_kopie_btn"):
                # "getvalue()" odczytuje zawartość przesłanego pliku jako
                # surowe bajty - dokładnie to, czego oczekuje nasza funkcja
                # waliduj_i_przywroc_baze() w database.py.
                sukces, komunikat = waliduj_i_przywroc_baze(wgrany_plik.getvalue())
                if sukces:
                    st.success(komunikat)
                else:
                    st.error(komunikat)


# --- EKRAN 1: WYBÓR PLANU TRENINGOWEGO + EDYCJA W PRAWYM GÓRNYM ROGU ---
elif st.session_state.page == "select_day":
    col_top_back, col_top_edit = st.columns([2, 1])

    if col_top_back.button("⬅️ Wróć do Menu", key="back_to_menu_from_select"):
        st.session_state.editing_plan_key = None
        go_to_menu()
        st.rerun()

    edit_btn_label = "🔓 Edycja ON" if st.session_state.edit_mode_plans else "🔒 Edycja"
    if col_top_edit.button(edit_btn_label, key="toggle_btn_plans"):
        st.session_state.edit_mode_plans = not st.session_state.edit_mode_plans
        st.session_state.editing_plan_key = None
        if not st.session_state.edit_mode_plans:
            st.session_state.is_admin_unlocked = False
        st.rerun()

    st.header("Wybierz dzień z planu:")

    if st.session_state.edit_mode_plans and not st.session_state.is_admin_unlocked:
        st.info("🔐 Tryb edycji wymaga podania hasła administratora.")
        admin_password = st.text_input("Wpisz hasło:", type="password", key="admin_pass_plans")
        if st.button("Odblokuj", key="unlock_plans_btn"):
            if admin_password == "admin":
                st.session_state.is_admin_unlocked = True
                st.rerun()
            else:
                st.error("Błędne hasło! Wpisz: admin")

    if not st.session_state.edit_mode_plans or st.session_state.is_admin_unlocked:
        if st.session_state.edit_mode_plans:
            with st.expander("➕ Dodaj nowy plan treningowy"):
                new_plan_name = st.text_input("Nazwa planu:", key="input_new_plan_name")
                if st.button("💾 Stwórz plan", key="btn_create_plan"):
                    if new_plan_name.strip():
                        new_key = f"plan_{datetime.now().timestamp()}"
                        st.session_state.workout_days.append({
                            "day_key": new_key,
                            "title": new_plan_name.strip(),
                            "label": f"✨ {new_plan_name.strip()}",
                            "exercises": [],
                            "is_default": False
                        })
                        persist_workout_days()  # NOWOŚĆ: zapisujemy nowy plan na trwałe
                        st.rerun()
                    else:
                        st.warning("Nazwa planu nie może być pusta.")
            st.markdown("---")

        for idx, day in enumerate(st.session_state.workout_days):
            is_locked = day.get("is_default", False)

            if not st.session_state.edit_mode_plans:
                if st.button(day["label"], key=f"day_clean_{day['day_key']}"):
                    go_to_exercise_list(day)
                    st.rerun()
            else:
                if is_locked:
                    col_l1, col_l2 = st.columns([5, 1])
                    if col_l1.button(f"🔒 {day['label']}", key=f"day_locked_{day['day_key']}"):
                        go_to_exercise_list(day)
                        st.rerun()
                    col_l2.caption("Baza")
                else:
                    col_b, col_e, col_d = st.columns([3, 1, 1])
                    if col_b.button(f"▶ {day['label']}", key=f"day_custom_{day['day_key']}"):
                        go_to_exercise_list(day)
                        st.rerun()
                    if col_e.button("✏️", key=f"edit_plan_{day['day_key']}"):
                        st.session_state.editing_plan_key = day['day_key']
                        st.rerun()
                    if col_d.button("❌", key=f"del_plan_{day['day_key']}"):
                        st.session_state.workout_days.pop(idx)
                        if st.session_state.editing_plan_key == day['day_key']:
                            st.session_state.editing_plan_key = None
                        persist_workout_days()  # NOWOŚĆ: zapisujemy usunięcie na trwałe
                        st.rerun()

    if st.session_state.editing_plan_key:
        target_plan = next(
            (p for p in st.session_state.workout_days if p['day_key'] == st.session_state.editing_plan_key), None)
        if target_plan:
            st.markdown("---")
            st.info(f"Edytujesz plan: {target_plan['title']}")
            new_p_name = st.text_input("Nowa nazwa:", value=target_plan['title'], key="input_edit_plan_val")
            col_sp, col_cp = st.columns(2)
            if col_sp.button("💾 Zapisz", key="btn_save_plan_edit"):
                if new_p_name.strip():
                    target_plan['title'] = new_p_name.strip()
                    target_plan['label'] = f"✨ {new_p_name.strip()}"
                    st.session_state.editing_plan_key = None
                    persist_workout_days()  # NOWOŚĆ: zapisujemy zmianę nazwy na trwałe
                    st.rerun()
                else:
                    st.warning("Nazwa nie może być pusta.")
            if col_cp.button("Anuluj", key="btn_cancel_plan_edit"):
                st.session_state.editing_plan_key = None
                st.rerun()


# --- EKRAN 2: LISTA ĆWICZEŃ W PLANIE + EDYCJA W PRAWYM GÓRNYM ROGU ---
elif st.session_state.page == "exercise_list":
    col_top_back_ex, col_top_edit_ex = st.columns([2, 1])

    if col_top_back_ex.button("⬅️ Wróć do planów", key="back_to_select_day"):
        st.session_state.editing_ex_key = None
        go_to_workout_day_selection()
        st.rerun()

    edit_btn_label_ex = "🔓 Edycja ON" if st.session_state.edit_mode_ex else "🔒 Edycja"
    if col_top_edit_ex.button(edit_btn_label_ex, key="toggle_btn_ex"):
        st.session_state.edit_mode_ex = not st.session_state.edit_mode_ex
        st.session_state.editing_ex_key = None
        if not st.session_state.edit_mode_ex:
            st.session_state.is_admin_unlocked = False
        st.rerun()

    current_day = next((d for d in st.session_state.workout_days if d["day_key"] == st.session_state.current_day_key),
                       None)

    if not current_day:
        st.error("Nie znaleziono planu treningowego.")
        if st.button("Wróć do menu"):
            go_to_menu()
            st.rerun()
    else:
        st.subheader(f"Plan: {current_day['title']}")

        if st.session_state.edit_mode_ex and not st.session_state.is_admin_unlocked:
            st.info("🔐 Tryb edycji ćwiczeń wymaga podania hasła administratora.")
            admin_password_ex = st.text_input("Wpisz hasło:", type="password", key="admin_pass_ex")
            if st.button("Odblokuj edycję", key="unlock_ex_btn"):
                if admin_password_ex == "admin":
                    st.session_state.is_admin_unlocked = True
                    st.rerun()
                else:
                    st.error("Błędne hasło! Wpisz: admin")

        if not st.session_state.edit_mode_ex or st.session_state.is_admin_unlocked:
            if st.session_state.edit_mode_ex:
                with st.expander("➕ Dodaj nowe ćwiczenie do tego planu"):
                    new_ex_name = st.text_input("Nazwa ćwiczenia:", key="input_new_ex_name")
                    if st.button("💾 Dodaj ćwiczenie", key="btn_add_to_day"):
                        if new_ex_name.strip():
                            new_key = f"ex_{datetime.now().timestamp()}"
                            current_day["exercises"].append({
                                "key": new_key,
                                "name": new_ex_name.strip(),
                                "image": "",
                                "note": "Ćwiczenie niestandardowe",
                                "is_default": False
                            })
                            persist_workout_days()  # NOWOŚĆ: zapisujemy nowe ćwiczenie na trwałe
                            st.rerun()
                        else:
                            st.warning("Nazwa nie może być pusta.")
                st.markdown("---")

            st.markdown("### Ćwiczenia:")

            if not current_day["exercises"]:
                st.info("Brak ćwiczeń w tym planie.")
            else:
                for idx, ex in enumerate(current_day["exercises"]):
                    is_ex_locked = ex.get("is_default", False)

                    if not st.session_state.edit_mode_ex:
                        if st.button(f"▶ {ex['name']}", key=f"go_ex_clean_{ex['key']}"):
                            go_to_exercise(ex)
                            st.rerun()
                    else:
                        if is_ex_locked and not st.session_state.is_admin_unlocked:
                            col_btn, col_lock = st.columns([5, 1])
                            if col_btn.button(f"🔒 {ex['name']}", key=f"go_ex_locked_{ex['key']}"):
                                go_to_exercise(ex)
                                st.rerun()
                            col_lock.markdown("🔒")
                        else:
                            col_btn, col_edit, col_del = st.columns([3, 1, 1])
                            if col_btn.button(f"▶ {ex['name']}", key=f"go_ex_{ex['key']}"):
                                go_to_exercise(ex)
                                st.rerun()
                            if col_edit.button("✏️", key=f"edit_ex_trigger_{ex['key']}"):
                                st.session_state.editing_ex_key = ex['key']
                                st.rerun()
                            if col_del.button("❌", key=f"del_ex_{ex['key']}"):
                                current_day["exercises"].pop(idx)
                                if st.session_state.editing_ex_key == ex['key']:
                                    st.session_state.editing_ex_key = None
                                persist_workout_days()  # NOWOŚĆ: zapisujemy usunięcie na trwałe
                                st.rerun()

        if st.session_state.editing_ex_key:
            target_ex = next((x for x in current_day["exercises"] if x['key'] == st.session_state.editing_ex_key), None)
            if target_ex:
                st.markdown("---")
                st.info(f"Edytujesz: {target_ex['name']}")
                new_ex_edited_name = st.text_input("Nowa nazwa ćwiczenia:", value=target_ex['name'],
                                                   key="input_edit_ex_val")
                col_se, col_ce = st.columns(2)
                if col_se.button("💾 Zapisz", key="btn_save_ex_edit"):
                    if new_ex_edited_name.strip():
                        target_ex['name'] = new_ex_edited_name.strip()
                        st.session_state.editing_ex_key = None
                        persist_workout_days()  # NOWOŚĆ: zapisujemy zmianę nazwy na trwałe
                        st.rerun()
                    else:
                        st.warning("Nazwa nie może być pusta.")
                if col_ce.button("Anuluj", key="btn_cancel_ex_edit"):
                    st.session_state.editing_ex_key = None
                    st.rerun()


# --- EKRAN 3: AKTYWNE ĆWICZENIE ---
elif st.session_state.page == "active_exercise":
    if st.button("⬅️ Wróć do listy ćwiczeń", key="back_to_exercise_list"):
        current_day_data = next(
            (d for d in st.session_state.workout_days if d["day_key"] == st.session_state.current_day_key),
            st.session_state.workout_days[0])
        go_to_exercise_list(current_day_data)
        st.rerun()

    ex = st.session_state.current_exercise
    ex_name = ex['name']

    st.title(ex_name)

    image_path = ex.get("image", "")
    if image_path and os.path.exists(image_path):
        st.image(image_path, use_container_width=True)

    if ex.get("note"):
        st.info(ex["note"])

    st.markdown("### 📝 Wpisz wyniki")

    sets_count_key = f"sets_{ex['key']}"
    if sets_count_key not in st.session_state:
        st.session_state[sets_count_key] = DEFAULT_SETS

    prefill_key = f"prefilled_{ex['key']}"
    if prefill_key not in st.session_state:
        today_sets = get_today_sets(ex_name, TODAY)
        for set_num, w, r in today_sets:
            st.session_state[f"w_{ex['key']}_{set_num}"] = w
            st.session_state[f"r_{ex['key']}_{set_num}"] = r
            if set_num > st.session_state[sets_count_key]:
                st.session_state[sets_count_key] = set_num
        st.session_state[prefill_key] = True

    sets_data = []

    # Potrzebujemy "day_tab" (klucz dnia, np. "pull") już TERAZ, przy każdym
    # pojedynczym zapisie serii - a nie tylko na samym końcu jak wcześniej.
    current_day_data = next(
        (d for d in st.session_state.workout_days if d["day_key"] == st.session_state.current_day_key),
        st.session_state.workout_days[0])

    col_h1, col_h2 = st.columns(2)
    col_h1.caption("⚖️ Ciężar (kg)")
    col_h2.caption("🔢 Powtórzenia")

    for i in range(1, st.session_state[sets_count_key] + 1):
        # ------------------------------------------------------------------
        # WAŻNE (naprawa błędu StreamlitWidgetAlreadyInstantiatedError):
        # Streamlit NIE pozwala zmieniać session_state pola PO tym, jak to
        # pole zostało już narysowane w tym samym przebiegu skryptu. Dlatego
        # reset wartości (po kliknięciu "Usuń") NIE MOŻE się dziać w bloku
        # przycisku poniżej (bo tam pole już by istniało) - musi się zdarzyć
        # TUTAJ, na samej górze pętli, ZANIM poniższe st.number_input() w
        # ogóle zostaną utworzone. Przycisk "Usuń" tylko ustawia prostą
        # flagę (osobny klucz, niezwiązany z żadnym polem) i każe appce się
        # przeładować - a dopiero NOWY przebieg skryptu, w tym miejscu,
        # faktycznie zeruje wartości, zanim pola zdążą powstać.
        flaga_resetu_klucz = f"zresetuj_{ex['key']}_{i}"
        if st.session_state.get(flaga_resetu_klucz, False):
            st.session_state[f"w_{ex['key']}_{i}"] = 0.0
            st.session_state[f"r_{ex['key']}_{i}"] = 0
            st.session_state[flaga_resetu_klucz] = False

        col1, col2 = st.columns(2)

        weight = col1.number_input(
            f"Waga {i}", min_value=0.0, step=1.25, key=f"w_{ex['key']}_{i}", label_visibility="collapsed"
        )
        reps = col2.number_input(
            f"Powt {i}", min_value=0, step=1, key=f"r_{ex['key']}_{i}", label_visibility="collapsed"
        )
        sets_data.append({"set_number": i, "weight": weight, "reps": reps})

        if weight > 0 and reps > 0:
            rep_max = weight * (1 + reps / 30)
            st.caption(f"Szacowany max (1RM): **{rep_max:.1f} kg**")

        # ------------------------------------------------------------------
        # Dwa przyciski obok siebie: ZAPISZ i USUŃ tę konkretną serię.
        # ------------------------------------------------------------------
        col_zapisz, col_usun = st.columns(2)

        # "💾 Zapisz" - zapisuje TĘ JEDNĄ serię do bazy danych od razu
        # (funkcja save_single_set w database.py) - nie trzeba czekać do
        # końca całego ćwiczenia. Dzięki temu, jeśli telefon przeładuje
        # appkę zaraz po tym (np. wracasz z innej aplikacji), ta seria JUŻ
        # jest bezpiecznie zapisana. Jeśli zmienisz wartości i klikniesz
        # ponownie - to też jest sposób na EDYCJĘ już zapisanej serii,
        # bo save_single_set nadpisuje poprzedni wpis tego samego numeru.
        if col_zapisz.button(f"💾 Zapisz {i}", key=f"save_set_{ex['key']}_{i}"):
            zapisano = save_single_set(
                TODAY, current_day_data["day_key"], ex_name, i, weight, reps
            )
            if zapisano:
                st.toast(f"Zapisano serię {i}! 💪", icon="✅")
                # Uruchamiamy (albo restartujemy, jeśli już trwał) stoper
                # odpoczynku - patrz pokaz_stoper_odpoczynku() na górze pliku.
                st.session_state.stoper_widoczny = True
                st.session_state.stoper_nonce += 1
                st.rerun()
            else:
                st.warning("Wpisz ciężar lub powtórzenia przed zapisem tej serii.")

        # "🗑️ Usuń" - NOWOŚĆ: kasuje tę serię zarówno z bazy danych, jak i
        # z pól na ekranie (przydatne np. gdy dodałeś serię 4, a jednak
        # zrobiłeś dziś tylko 3, albo pomyliłeś się przy wpisywaniu).
        if col_usun.button(f"🗑️ Usuń {i}", key=f"del_set_{ex['key']}_{i}"):
            # Zapisanie 0/0 dla tego numeru serii = funkcja save_single_set
            # sama skasuje wiersz z bazy (patrz warunek "weight>0 or reps>0"
            # w database.py) i nic nowego nie wstawi.
            save_single_set(TODAY, current_day_data["day_key"], ex_name, i, 0.0, 0)
            # NIE zerujemy tu pól bezpośrednio (patrz duży komentarz na
            # górze pętli "for i in ...") - zamiast tego tylko ustawiamy
            # flagę. Faktyczne wyzerowanie pól zrobi się SAMO na początku
            # NASTĘPNEGO przebiegu skryptu, zanim pola zostaną narysowane.
            st.session_state[f"zresetuj_{ex['key']}_{i}"] = True
            st.toast(f"Usunięto serię {i}", icon="🗑️")
            st.rerun()

        st.divider()

    if st.button("➕ Dodaj serię", key="add_set_btn"):
        st.session_state[sets_count_key] += 1
        st.rerun()

    # --- Stoper odpoczynku - pokazuje się po zapisaniu dowolnej serii -------
    if st.session_state.stoper_widoczny:
        pokaz_stoper_odpoczynku(st.session_state.stoper_nonce)
        if st.button("❌ Ukryj stoper", key="ukryj_stoper_btn"):
            st.session_state.stoper_widoczny = False
            st.rerun()

    st.markdown("---")
    if st.button("✅ Zapisz wszystko i wróć do listy", type="primary", key="save_exercise_btn"):
        # Ten przycisk to już tylko "domknięcie" ćwiczenia - zapisuje
        # wszystkie aktualnie wypełnione pola na raz (na wypadek, gdybyś
        # czegoś nie zapisał pojedynczo) i wraca do listy ćwiczeń.
        save_exercise_sets(TODAY, current_day_data["day_key"], ex_name, sets_data)
        go_to_exercise_list(current_day_data)
        st.rerun()


# --- EKRAN 4: HISTORIA I WYKRESY PROGRESU ---
elif st.session_state.page == "history":
    if st.button("⬅️ Wróć do Menu", key="back_to_menu_from_history"):
        go_to_menu()
        st.rerun()

    st.header("📚 Historia Treningów")

    sessions = get_all_sessions()
    if not sessions:
        st.info("Brak zapisanych treningów w bazie. Czas zacząć ćwiczyć!")
    else:
        for sess in sessions:
            date_str = sess["date"]
            day_tab = sess["day_tab"]

            with st.expander(f"📅 Trening: {date_str} ({day_tab.upper()})"):
                exercises_in_session = get_exercises_for_session(date_str)
                for ex_name in exercises_in_session:
                    st.markdown(f"**{ex_name}**")
                    sets = get_sets_for_date(ex_name, date_str)
                    sets_str = " · ".join(f"{w:g}kg × {r}" for (_, w, r) in sets)
                    st.caption(f"Serie: {sets_str}")

                    prog_data = get_progress_data(ex_name)
                    if len(prog_data) > 1:
                        st.write("📈 *Progres maksymalnego ciężaru:*")
                        chart_data = {row["date"]: row["max_weight"] for row in prog_data}
                        st.line_chart(chart_data)