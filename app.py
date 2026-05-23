import streamlit as st
import websocket
import threading
import google.generativeai as genai

st.set_page_config(layout="wide")

# Конфигурация на Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
except:
    st.error("Грешка при Gemini API ключа!")

st.title("⚽ Bzzoiro AI Live Analytics")

# Фонова нишка за WebSocket
if 'ws_started' not in st.session_state:
    st.session_state.live_data = "Свързвам се..."
    st.session_state.ws_started = True
    
    def run_websocket():
        def on_message(ws, message):
            st.session_state.live_data = message
        
        ws = websocket.WebSocketApp("wss://sports.bzzoiro.com/ws/live/", on_message=on_message)
        ws.run_forever()

    threading.Thread(target=run_websocket, daemon=True).start()

st.write(f"Данни на живо: {st.session_state.live_data}")

if st.button("Анализирай"):
    try:
        response = model.generate_content(f"Анализирай тези данни за залог: {st.session_state.live_data}")
        st.write(response.text)
    except Exception as e:
        st.write(f"Грешка: {e}")
