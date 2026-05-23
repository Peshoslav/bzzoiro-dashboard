import streamlit as st
import websocket
import threading
import json
from google import genai
from streamlit.runtime.scriptrunner import add_script_run_ctx

st.set_page_config(layout="wide", page_title="Bzzoiro Live AI")

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Грешка при Gemini ключа")

st.title("⚽ Bzzoiro AI Live Analytics")

if 'live_data' not in st.session_state:
    st.session_state.live_data = "Свързвам се..."

def run_websocket():
    url = "wss://sports.bzzoiro.com/ws/live/"
    
    def on_message(ws, message):
        # Това обновява състоянието и казва на Streamlit да се опресни
        st.session_state.live_data = message
        # Понякога е нужно леко закъснение, за да се види ефекта
        
    def on_open(ws):
        auth_payload = {"action": "auth", "api_key": st.secrets["BZZOIRO_API_KEY"]}
        ws.send(json.dumps(auth_payload))
        st.session_state.live_data = "Авторизация изпратена..."

    ws = websocket.WebSocketApp(url, on_message=on_message, on_open=on_open)
    ws.run_forever()

if 'ws_started' not in st.session_state:
    t = threading.Thread(target=run_websocket, daemon=True)
    add_script_run_ctx(t) # ТОВА Е ТАЙНАТА: Свързва нишката със сайта
    t.start()
    st.session_state.ws_started = True

st.write(f"### Статус: {st.session_state.live_data}")

if st.button("Анализирай мача"):
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=f"Ти си футболен анализатор. Дай съвет за тези данни: {st.session_state.live_data}"
        )
        st.write("### AI Анализ:")
        st.write(response.text)
    except Exception as e:
        st.error(f"Грешка: {e}")
