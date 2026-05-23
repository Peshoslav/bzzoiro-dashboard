import streamlit as st
import websocket
import threading
import json
import time
from google import genai 

# Настройка на страницата
st.set_page_config(layout="wide", page_title="Bzzoiro Live AI")

# Конфигурация на Gemini (използваме новата библиотека)
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    model_name = "gemini-3.1-flash-lite"
except Exception as e:
    st.error(f"Грешка при конфигурация на Gemini: {e}")

st.title("⚽ Bzzoiro AI Live Analytics")

# Инициализация на състоянието за данни
if 'live_data' not in st.session_state:
    st.session_state.live_data = "Очаквам старт..."

# Логика за WebSocket
def run_websocket():
    url = "wss://sports.bzzoiro.com/ws/live/"
    
    def on_message(ws, message):
        st.session_state.live_data = message
        
    def on_open(ws):
        # Авторизация чрез изпращане на JSON съобщение, както изисква документацията
        auth_payload = {
            "action": "auth",
            "api_key": st.secrets["BZZOIRO_API_KEY"]
        }
        ws.send(json.dumps(auth_payload))
        st.session_state.live_data = "Авторизация изпратена, очакване на поток..."
        
    def on_error(ws, error):
        st.session_state.live_data = f"WebSocket грешка: {error}"

    ws = websocket.WebSocketApp(
        url, 
        on_message=on_message,
        on_open=on_open,
        on_error=on_error
    )
    ws.run_forever()

# Стартиране на WebSocket в отделна нишка
if 'ws_started' not in st.session_state:
    threading.Thread(target=run_websocket, daemon=True).start()
    st.session_state.ws_started = True

# Интерфейс
st.write(f"**Статус на данни:** {st.session_state.live_data}")

if st.button("Анализирай с Gemini"):
    try:
        # Извикване на модела за анализ
        response = client.models.generate_content(
            model=model_name,
            contents=f"Ти си футболен анализатор. Дай кратък, професионален съвет за тези данни на живо: {st.session_state.live_data}"
        )
        st.write("### AI Анализ:")
        st.write(response.text)
    except Exception as e:
        st.error(f"Грешка при анализа: {e}")

# Бутон за ръчно обновяване на страницата (ако данните замръзнат)
if st.button("Обнови страницата"):
    st.rerun()
