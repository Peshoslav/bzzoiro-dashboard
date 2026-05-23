import streamlit as st
import websocket
import json
import threading
import google.generativeai as genai

# Конфигурация
st.set_page_config(page_title="Bzzoiro Live AI", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

st.title("⚽ Bzzoiro AI Live Analytics")

# Функция за анализ чрез Gemini
def analyze_match(match_data):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Анализирай този футболен мач на живо и дай кратък съвет за залог: {match_data}"
    response = model.generate_content(prompt)
    return response.text

# Логика за WebSocket връзка (работи във фонов режим)
if 'live_data' not in st.session_state:
    st.session_state.live_data = "Чакам данни..."

def on_message(ws, message):
    st.session_state.live_data = message # Тук ще обработваме JSON данните

# Основен интерфейс
st.write(f"Текущи данни от WebSocket: {st.session_state.live_data}")

if st.button("Анализирай с Gemini"):
    analysis = analyze_match(st.session_state.live_data)
    st.write("### AI Съвет:")
    st.info(analysis)
