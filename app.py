# ============================================================================
# app.py - WERSJA Z PROSTYM ZARZÄDZANIEM (Dodaj / Edytuj / UsuÅ„)
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

if "custom_exercises" not in st.session_state:
    st.session_state.custom_exercises = []


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

    for day in WORKOUT_DAYS:
        if st.button(day["label"], key=f"day_{day['day_key']}"):
            st.toast(f"🔥 Odpalamy plan: {day['title']}!", icon="💪")
            go_to_exercise_list(day)
            st.rerun()


# --- EKRAN 2: WYBÓR ĆWICZENIA Z DANEGO DNIA + ZARZĄDZANIE ---
elif st.session_state.page == "exercise_list":
    if st.button("⬅️ Wróć do wyboru dnia", key="back_to_select_day"):
        go_to_workout_day_selection()
        st.rerun()

    current_day = st.session_state.current_day
    st.subheader(f"Zestaw: {current_day['title']}")

    # --- PANEL ZARZĄDZANIA WŁASNYMI ĆWICZENIAMI ---
    with st.expander("🛠️ Zarządzaj własnymi ćwiczeniami (Dodaj / Edytuj / Usuń)"):
        action = st.radio("Wybierz akcję:", ["➕ Dodaj nowe", "✏️ Edytuj nazwę", "❌ Usuń ćwiczenie"], horizontal=True,
                          key="cex_action_radio")

        # 1. DODawanie
        if action == "➕ Dodaj nowe":
            new_name = st.text_input("Nazwa nowego ćwiczenia:", key="input_add_cex")
            if st.button("💾 Zapisz nowe ćwiczenie", key="btn_confirm_add"):
                if new_name.strip():
                    new_key = f"custom_{datetime.now().timestamp()}"
                    st.session_state.custom_exercises.append({
                        "key": new_key,
                        "name": new_name.strip(),
                        "image": "",
                        "note": "Własne ćwiczenie niestandardowe"
                    })
                    st.toast("Dodano ćwiczenie!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Wpisz nazwę.")

        # 2. EDYCJA
        elif action == "✏️ Edytuj nazwę":
            if not st.session_state.custom_exercises:
                st.info("Brak własnych ćwiczeń do edycji.")
            else:
                cex_names = {cex['name']: cex for cex in st.session_state.custom_exercises}
                selected_to_edit = st.selectbox("Wybierz ćwiczenie do edycji:", list(cex_names.keys()),
                                                key="select_edit_cex")
                target = cex_names[selected_to_edit]

                updated_name = st.text_input("Nowa nazwa:", value=target['name'], key="input_edit_cex_name")
                if st.button("💾 Zaktualizuj nazwę", key="btn_confirm_edit"):
                    if updated_name.strip():
                        target['name'] = updated_name.strip()
                        st.toast("Zaktualizowano nazwę!", icon="💾")
                        st.rerun()
                    else:
                        st.warning("Nazwa nie może być pusta.")

        # 3. USUWANIE
        elif action == "❌ Usuń ćwiczenie":
            if not st.session_state.custom_exercises:
                st.info("Brak własnych ćwiczeń do usunięcia.")
            else:
                cex_names_del = {cex['name']: cex for cex in st.session_state.custom_exercises}
                selected_to_del = st.selectbox("Wybierz ćwiczenie do usunięcia:", list(cex_names_del.keys()),
                                               key="select_del_cex")

                if st.button("🗑️ Usuń trwale", type="primary", key="btn_confirm_del"):
                    target_to_remove = cex_names_del[selected_to_del]
                    st.session_state.custom_exercises = [x for x in st.session_state.custom_exercises if
                                                         x['key'] != target_to_remove['key']]
                    st.toast("Usunięto ćwiczenie!", icon="🗑️")
                    st.rerun()

    st.markdown("---")
    st.markdown("### Ćwiczenia z planu:")

    # Wyświetlanie domyślnych ćwiczeń z konfiguracji
    for ex in current_day["exercises"]:
        if st.button(f"▶ {ex['name']}", key=f"ex_{ex['key']}"):
            st.toast(f"🎯 Wybrałeś: {ex['name']}", icon="🏋️‍♂️")
            go_to_exercise(ex)
            st.rerun()

    # Wyświetlanie własnych, niestandardowych ćwiczeń
    if st.session_state.custom_exercises:
        st.markdown("### Twoje własne ćwiczenia:")
        for cex in st.session_state.custom_exercises:
            if st.button(f"▶ ⭐ {cex['name']}", key=f"ex_custom_{cex['key']}"):
                st.toast(f"🎯 Wybrałeś: {cex['name']}", icon="🏋️‍♂️")
                go_to_exercise(cex)
                st.rerun()


# --- EKRAN 3: AKTYWNE ĆWICZENIE ---
elif st.session_state.page == "active_exercise":
    if st.button("⬅️ Wróć do listy ćwiczeń", key="back_to_exercise_list"):
        go_to_exercise_list(st.session_state.current_day)
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
        save_exercise_sets(TODAY, st.session_state.current_day["day_key"], ex_name, sets_data)
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