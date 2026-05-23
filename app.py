import streamlit as st
import websocket
import threading
import time
from google import genai # Новата библиотека

st.set_page_config(layout="wide")

# Нова конфигурация за Gemini
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Грешка: {e}")

st.title("⚽ Bzzoiro AI Live Analytics")

# Фонова нишка за WebSocket
if 'live_data' not in st.session_state:
    st.session_state.live_data = "Свързвам се..."

# Заменете блока с run_websocket с този:
def run_websocket():
    # Опитваме да добавим ключа към адреса, ако Header не работи
    url = f"wss://sports.bzzoiro.com/ws/live/?api_key={st.secrets['BZZOIRO_API_KEY']}"
    
    def on_message(ws, message):
        st.session_state.live_data = message
        
    def on_open(ws):
        st.session_state.live_data = "Успешна връзка! Чакам данни..."

    ws = websocket.WebSocketApp(
        url, 
        on_message=on_message,
        on_open=on_open
    )
    ws.run_forever()

if 'ws_started' not in st.session_state:
    threading.Thread(target=run_websocket, daemon=True).start()
    st.session_state.ws_started = True

# Показваме данни (използваме st.empty, за да се обновява)
data_placeholder = st.empty()
data_placeholder.write(f"Текущи данни: {st.session_state.live_data}")

if st.button("Анализирай мача"):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Анализирай тези спортни данни за залог: {st.session_state.live_data}"
        )
        st.write("### AI Анализ:")
        st.write(response.text)
    except Exception as e:
        st.write(f"Грешка в анализа: {e}")
