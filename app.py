import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Bzzoiro Live Football")
st.title("⚽ Bzzoiro Live Football Dashboard")

# Функция за визуализация на мач с чат прозорец
def render_match(match_name, stats, live_score):
    with st.expander(f"🔴 {match_name} - {live_score}"):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("Статистики:", stats)
        with col2:
            st.text_area("AI Анализатор (Гемини)", "Анализирам мача в реално време...", height=100)
            st.button(f"Попитай за {match_name}")

# Примерни данни (скоро ще ги заменим с реални от Bzzoiro)
st.subheader("Мачове на живо")
render_match("Реал Мадрид - Барселона", "Притежание: 55% - 45%", "1:0")
