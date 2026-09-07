# ============================================================================
# app.py - PEŁNA EDYCJA PLANU (Edytuj, Usuń, Dodaj do zestawu)
# ============================================================================

import streamlit as st
from datetime import datetime
import copy
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
# 2. NAWIGACJA I STAN APLIKACJI (Session State)
# ----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "menu"

# Kopiujemy plan treningowy do pamięci sesji, aby można go było modyfikować w locie
if "workout_days" not in st.session_state:
    st.session_state.workout_days = copy.deepcopy(WORKOUT_DAYS)

if "editing_ex_key" not in st.session_state:
    st.session_state.editing_ex_key = None


def go_to_menu():
    st.session_state.page = "menu"


def go_to_workout_day_selection():
    st.session_state.page = "select_day"


def go_to_exercise_list(day_data):
    st.session_state.current_day_key = day_data["day_key"]
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

    if st.button("🔥 NOWY TRENING", type="primary", key="menu_new_workout"):
        st.toast("🚀 Zaczynamy nową sesję!", icon="⚡")
        go_to_workout_day_selection()
        st.rerun()

    if st.button("📚 HISTORIA I WYKRESY", key="menu_history"):
        st.toast("📊 Otwieram archiwum wyników", icon="📈")
        go_to_history()
        st.rerun()


# --- EKRAN 1: WYBÓR DNIA TRENINGOWEGO ---
elif st.session_state.page == "select_day":
    if st.button("⬅️ Wróć do Menu", key="back_to_menu_from_select"):
        go_to_menu()
        st.rerun()

    st.header("Wybierz dzień z planu:")

    for day in st.session_state.workout_days:
        if st.button(day["label"], key=f"day_{day['day_key']}"):
            st.toast(f"🔥 Odpalamy plan: {day['title']}!", icon="💪")
            go_to_exercise_list(day)
            st.rerun()


# --- EKRAN 2: LISTA ĆWICZEŃ W DANYM ZESTAWIE + EDYCJA / USUWANIE / DODAWANIE ---
elif st.session_state.page == "exercise_list":
    if st.button("⬅️ Wróć do wyboru dnia", key="back_to_select_day"):
        st.session_state.editing_ex_key = None
        go_to_workout_day_selection()
        st.rerun()

    # Znajdź aktualny dzień na podstawie zapisanego klucza
    current_day = next((d for d in st.session_state.workout_days if d["day_key"] == st.session_state.current_day_key),
                       None)

    if not current_day:
        st.error("Nie znaleziono zestawu treningowego.")
        if st.button("Wróć do menu"):
            go_to_menu()
            st.rerun()
    else:
        st.subheader(f"Zestaw: {current_day['title']}")

        # --- PANEL DODAWANIA NOWEGO ĆWICZENIA DO TEGO ZESTAWU ---
        with st.expander("➕ Dodaj nowe ćwiczenie do tego zestawu"):
            new_ex_name = st.text_input("Nazwa ćwiczenia:", key="input_new_ex_name")
            if st.button("💾 Zapisz i dodaj do planu", key="btn_add_to_day"):
                if new_ex_name.strip():
                    new_key = f"ex_{datetime.now().timestamp()}"
                    current_day["exercises"].append({
                        "key": new_key,
                        "name": new_ex_name.strip(),
                        "image": "",
                        "note": "Ćwiczenie dodane przez użytkownika"
                    })
                    st.toast("Dodano nowe ćwiczenie do zestawu!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Nazwa nie może być pusta.")

        st.markdown("---")
        st.markdown("### Ćwiczenia w tym zestawie:")
        st.caption("Kliknij ▶ aby ćwiczyć, albo użyj przycisków obok, aby edytować/usunąć.")

        # Wyświetlanie listy ćwiczeń z opcjami wyboru, edycji i usuwania
        for idx, ex in enumerate(current_day["exercises"]):
            col_btn, col_edit, col_del = st.columns([4, 1, 1])

            # Przycisk wejścia do ćwiczenia
            if col_btn.button(f"▶ {ex['name']}", key=f"go_ex_{ex['key']}"):
                st.toast(f"🎯 Wybrałeś: {ex['name']}", icon="🏋️‍♂️")
                go_to_exercise(ex)
                st.rerun()

            # Przycisk edycji (zmieniania nazwy)
            if col_edit.button("✏️", key=f"edit_trigger_{ex['key']}"):
                st.session_state.editing_ex_key = ex['key']
                st.rerun()

            # Przycisk usuwania z planu
            if col_del.button("❌", key=f"delete_ex_{ex['key']}"):
                current_day["exercises"].pop(idx)
                if st.session_state.editing_ex_key == ex['key']:
                    st.session_state.editing_ex_key = None
                st.toast("Usunięto ćwiczenie z planu", icon="🗑️")
                st.rerun()

        # Jeśli wybrano edycję konkretnego ćwiczenia, pokaż mały formularz pod spodem
        if st.session_state.editing_ex_key:
            target_key = st.session_state.editing_ex_key
            target_ex = next((x for x in current_day["exercises"] if x['key'] == target_key), None)

            if target_ex:
                st.markdown("---")
                st.info(f"Edytujesz nazwę dla: **{target_ex['name']}**")
                new_edited_name = st.text_input("Nowa nazwa ćwiczenia:", value=target_ex['name'],
                                                key=f"input_edit_val_{target_key}")

                col_save_ed, col_cancel_ed = st.columns(2)
                if col_save_ed.button("💾 Zapisz zmianę", key=f"save_edit_btn_{target_key}"):
                    if new_edited_name.strip():
                        target_ex['name'] = new_edited_name.strip()
                        st.session_state.editing_ex_key = None
                        st.toast("Zaktualizowano nazwę ćwiczenia!", icon="💾")
                        st.rerun()
                    else:
                        st.warning("Nazwa nie może być pusta.")
                if col_cancel_ed.button("Anuluj", key=f"cancel_edit_btn_{target_key}"):
                    st.session_state.editing_ex_key = None
                    st.rerun()


# --- EKRAN 3: AKTYWNE ĆWICZENIE ---
elif st.session_state.page == "active_exercise":
    if st.button("⬅️ Wróć do listy ćwiczeń", key="back_to_exercise_list"):
        # Wracamy do zestawu, z którego przeszliśmy
        current_day_data = next(
            (d for d in st.session_state.workout_days if d["day_key"] == st.session_state.current_day_key),
            WORKOUT_DAYS[0])
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

        if weight > 0 and reps > 0:
            rep_max = weight * (1 + reps / 30)
            st.caption(f"Szacowany max (1RM): **{rep_max:.1f} kg**")

    if st.button("➕ Dodaj serię", key="add_set_btn"):
        st.session_state[sets_count_key] += 1
        st.rerun()

    if st.button("💾 Zapisz ten wynik", type="primary", key="save_exercise_btn"):
        current_day_data = next(
            (d for d in st.session_state.workout_days if d["day_key"] == st.session_state.current_day_key),
            WORKOUT_DAYS[0])
        save_exercise_sets(TODAY, current_day_data["day_key"], ex_name, sets_data)
        st.toast("🔥 Zapisane! Pompa rośnie!", icon="💪")
        st.balloons()
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