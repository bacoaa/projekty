# ============================================================================
# app.py - CZYSTY WIDOK + PRZEŁĄCZNIK TRYBU EDYCJI (Kłódki i Opcje na żądanie)
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

if "workout_days" not in st.session_state:
    initial_days = copy.deepcopy(WORKOUT_DAYS)
    for d in initial_days:
        d["is_default"] = True
    st.session_state.workout_days = initial_days

if "editing_plan_key" not in st.session_state:
    st.session_state.editing_plan_key = None

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


# --- EKRAN 1: WYBÓR PLANU TRENINGOWEGO + TRYB EDYCJI ---
elif st.session_state.page == "select_day":
    if st.button("⬅️ Wróć do Menu", key="back_to_menu_from_select"):
        st.session_state.editing_plan_key = None
        go_to_menu()
        st.rerun()

    st.header("Wybierz dzień z planu:")

    # Przełącznik trybu edycji planów
    edit_mode_plans = st.toggle("⚙️ Włącz tryb edycji / zarządzania planami", key="toggle_edit_plans")

    # Panel dodawania nowego planu (widoczny tylko w trybie edycji)
    if edit_mode_plans:
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
                    st.toast("Utworzono nowy plan!", icon="✅")
                    st.rerun()
                else:
                    st.warning("Nazwa planu nie może być pusta.")
        st.markdown("---")

    # Wyświetlanie planów
    for idx, day in enumerate(st.session_state.workout_days):
        is_locked = day.get("is_default", False)

        if not edit_mode_plans:
            # Tryb normalny - tylko czyste przyciski kafelkowe
            if st.button(day["label"], key=f"day_clean_{day['day_key']}"):
                st.toast(f"🔥 Odpalamy plan: {day['title']}!", icon="💪")
                go_to_exercise_list(day)
                st.rerun()
        else:
            # Tryb edycji - z kłódkami dla domyślnych i opcjami usuwania/edycji dla własnych
            if is_locked:
                col_l1, col_l2 = st.columns([5, 1])
                if col_l1.button(f"🔒 {day['label']}", key=f"day_locked_{day['day_key']}"):
                    go_to_exercise_list(day)
                    st.rerun()
                col_l2.caption("Zablokowany")
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
                    st.toast("Usunięto plan", icon="🗑️")
                    st.rerun()

    # Formularz edycji nazwy planu niestandardowego
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
                    st.toast("Zaktualizowano nazwę!", icon="💾")
                    st.rerun()
                else:
                    st.warning("Nazwa nie może być pusta.")
            if col_cp.button("Anuluj", key="btn_cancel_plan_edit"):
                st.session_state.editing_plan_key = None
                st.rerun()


# --- EKRAN 2: LISTA ĆWICZEŃ W DANYM PLANIE + TRYB EDYCJI ---
elif st.session_state.page == "exercise_list":
    if st.button("⬅️ Wróć do wyboru planu", key="back_to_select_day"):
        st.session_state.editing_ex_key = None
        go_to_workout_day_selection()
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

        # Przełącznik trybu edycji ćwiczeń
        edit_mode_exercises = st.toggle("⚙️ Włącz tryb edycji / dodawania ćwiczeń", key="toggle_edit_ex")

        # Panel dodawania ćwiczenia (widoczny w trybie edycji)
        if edit_mode_exercises:
            with st.expander("➕ Dodaj nowe ćwiczenie do tego planu"):
                new_ex_name = st.text_input("Nazwa ćwiczenia:", key="input_new_ex_name")
                if st.button("💾 Dodaj ćwiczenie", key="btn_add_to_day"):
                    if new_ex_name.strip():
                        new_key = f"ex_{datetime.now().timestamp()}"
                        current_day["exercises"].append({
                            "key": new_key,
                            "name": new_ex_name.strip(),
                            "image": "",
                            "note": "Ćwiczenie niestandardowe"
                        })
                        st.toast("Dodano ćwiczenie!", icon="✅")
                        st.rerun()
                    else:
                        st.warning("Nazwa nie może być pusta.")
            st.markdown("---")

        st.markdown("### Ćwiczenia:")

        if not current_day["exercises"]:
            st.info("Brak ćwiczeń w tym planie.")
        else:
            for idx, ex in enumerate(current_day["exercises"]):
                if not edit_mode_exercises:
                    # Czysty przycisk ćwiczenia
                    if st.button(f"▶ {ex['name']}", key=f"go_ex_clean_{ex['key']}"):
                        st.toast(f"🎯 Wybrałeś: {ex['name']}", icon="🏋️‍♂️")
                        go_to_exercise(ex)
                        st.rerun()
                else:
                    # Tryb edycji z opcją edycji nazwy i usuwania
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
                        st.toast("Usunięto ćwiczenie", icon="🗑️")
                        st.rerun()

        # Formularz edycji nazwy ćwiczenia
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
                        st.toast("Zaktualizowano nazwę!", icon="💾")
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
            st.session_state.workout_days[0])
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