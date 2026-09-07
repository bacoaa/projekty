# ============================================================================
# app.py - WERSJA FINALNA Z ANIMACJAMI KLIKNIĘĆ I STARTU
# ============================================================================

import streamlit as st
from datetime import datetime
import os

from database import (
    init_db, save_exercise_sets, get_history, get_today_sets,
    get_all_sessions, get_exercises_for_session, get_sets_for_date, get_progress_data
)
from exercises_config import WORKOUT_DAYS, MAX_SETS

# Domyślna liczba serii na start: 3
DEFAULT_SETS = 3

TODAY = datetime.now().strftime("%Y-%m-%d")

# ----------------------------------------------------------------------------
# 1. KONFIGURACJA STRONY I STYLÓW CSS
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Dziennik Treningowy", page_icon="💪", layout="centered")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 4rem !important; 
            padding-bottom: 3rem;
            max-width: 600px;
        }
        div.stButton > button {
            width: 100%;
            border-radius: 10px;
            font-weight: bold;
            border: 1px solid #444;
        }
        div.stButton > button[kind="primary"] {
            background-color: #ff4b4b;
            color: white;
            border: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()

# ----------------------------------------------------------------------------
# 2. NAWIGACJA (SESSION STATE)
# ----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "menu"


def go_to_menu():
    st.session_state.page = "menu"


def go_to_workout_day_selection():
    st.session_state.page = "select_day"


def go_to_exercise_list(day_key):
    st.session_state.current_day = day_key
    st.session_state.page = "exercise_list"


def go_to_exercise(exercise_data):
    st.session_state.current_exercise = exercise_data
    st.session_state.page = "active_exercise"


def go_to_history():
    st.session_state.page = "history"


# ----------------------------------------------------------------------------
# 3. WIDOKI APLIKACJI
# ----------------------------------------------------------------------------

# --- EKRAN 0: MENU GŁÓWNE ---
if st.session_state.page == "menu":
    st.title("💪 Twój Dziennik")
    st.write("Wybierz, co robimy dzisiaj:")

    if st.button("🔥 NOWY TRENING", type="primary"):
        st.toast("🚀 Zaczynamy nową sesję!", icon="⚡")
        go_to_workout_day_selection()
        st.rerun()

    if st.button("📚 HISTORIA I WYKRESY"):
        st.toast("📊 Otwieram archiwum wyników", icon="📈")
        go_to_history()
        st.rerun()


# --- EKRAN 1: WYBÓR DNIA TRENINGOWEGO ---
elif st.session_state.page == "select_day":
    if st.button("⬅️ Wróć do Menu"):
        go_to_menu()
        st.rerun()

    st.header("Wybierz dzień z planu:")

    for day in WORKOUT_DAYS:
        if st.button(day["label"], key=f"day_{day['day_key']}"):
            st.toast(f"🔥 Odpalamy plan: {day['title']}!", icon="💪")
            go_to_exercise_list(day)
            st.rerun()


# --- EKRAN 2: WYBÓR ĆWICZENIA Z DANEGO DNIA ---
elif st.session_state.page == "exercise_list":
    if st.button("⬅️ Wróć do wyboru dnia"):
        go_to_workout_day_selection()
        st.rerun()

    current_day = st.session_state.current_day
    st.subheader(f"Zestaw: {current_day['title']}")

    for ex in current_day["exercises"]:
        if st.button(f"▶ {ex['name']}", key=f"ex_{ex['key']}"):
            st.toast(f"🎯 Wybrałeś: {ex['name']}", icon="🏋️‍♂️")
            go_to_exercise(ex)
            st.rerun()


# --- EKRAN 3: AKTYWNE ĆWICZENIE ---
elif st.session_state.page == "active_exercise":
    if st.button("⬅️ Wróć do listy ćwiczeń"):
        go_to_exercise_list(st.session_state.current_day)
        st.rerun()

    ex = st.session_state.current_exercise
    ex_name = ex['name']

    st.title(ex_name)

    # Obsługa zdjęć i GIF-ów
    image_path = ex.get("image", "")
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)
    else:
        st.caption(f"Brak pliku: {image_path}")

    if ex.get("note"):
        st.info(ex["note"])

    st.markdown("### 📝 Wpisz wyniki")

    sets_count_key = f"sets_{ex['key']}"
    if sets_count_key not in st.session_state:
        st.session_state[sets_count_key] = DEFAULT_SETS

    # Prefill dzisiejszych wyników z bazy
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

    col_h1, col_h2 = st.columns(2)
    col_h1.caption("⚖️ Ciężar (kg)")
    col_h2.caption("🔢 Powtórzenia")

    for i in range(1, st.session_state[sets_count_key] + 1):
        col1, col2 = st.columns(2)

        weight = col1.number_input(
            f"Waga {i}", min_value=0.0, step=1.25, key=f"w_{ex['key']}_{i}", label_visibility="collapsed"
        )
        reps = col2.number_input(
            f"Powt {i}", min_value=0, step=1, key=f"r_{ex['key']}_{i}", label_visibility="collapsed"
        )
        sets_data.append({"set_number": i, "weight": weight, "reps": reps})

        # Kalkulator 1RM na żywo
        if weight > 0 and reps > 0:
            rep_max = weight * (1 + reps / 30)
            st.caption(f"Szacowany max (1RM): **{rep_max:.1f} kg**")

    if st.button("➕ Dodaj serię"):
        st.session_state[sets_count_key] += 1
        st.rerun()

    # Zapis z satysfakcjonującymi animacjami (balony + toast)
    if st.button("💾 Zapisz ten wynik", type="primary"):
        save_exercise_sets(TODAY, st.session_state.current_day["day_key"], ex_name, sets_data)
        st.toast("🔥 Zapisane! Pompa rośnie!", icon="💪")
        st.balloons()
        st.rerun()


# --- EKRAN 4: HISTORIA I WYKRESY PROGRESU ---
elif st.session_state.page == "history":
    if st.button("⬅️ Wróć do Menu"):
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