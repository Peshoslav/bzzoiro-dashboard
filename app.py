import streamlit as st
import websocket
import threading
import time
from google import genai 

st.set_page_config(layout="wide")

# Използваме модела с най-добра квота: gemini-3.1-flash-lite
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    model_name = "gemini-3.1-flash-lite"
except Exception as e:
    st.error(f"Грешка при конфигурация: {e}")

st.title("⚽ Bzzoiro AI Live Analytics")

# WebSocket логика - опитваме с директен URL параметър
if 'live_data' not in st.session_state:
    st.session_state.live_data = "Чакам данни от Bzzoiro..."

def run_websocket():
    # Повечето спортни API-та изискват API ключа в URL параметър
    url = f"wss://sports.bzzoiro.com/ws/live/?token={st.secrets['BZZOIRO_API_KEY']}"
    
    def on_message(ws, message):
        st.session_state.live_data = message
    
    ws = websocket.WebSocketApp(url, on_message=on_message)
    ws.run_forever()

if 'ws_started' not in st.session_state:
    threading.Thread(target=run_websocket, daemon=True).start()
    st.session_state.ws_started = True

st.write(f"**Статус на данни:** {st.session_state.live_data}")

if st.button("Анализирай мача"):
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=f"Ти си футболен анализатор. Дай кратък, професионален съвет за тези данни: {st.session_state.live_data}"
        )
        st.write("### AI Анализ:")
        st.write(response.text)
    except Exception as e:
        st.error(f"Грешка при анализа: {e}")
