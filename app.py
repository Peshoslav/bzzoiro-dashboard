import streamlit as st
import websocket
import threading
import google.generativeai as genai

st.set_page_config(layout="wide")

# Поправка за Gemini: Използваме 'gemini-1.5-flash'
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Грешка при конфигурация на Gemini: {e}")

st.title("⚽ Bzzoiro AI Live Analytics")

# Фонова нишка за WebSocket с добавен API Key в Header-а
if 'ws_started' not in st.session_state:
    st.session_state.live_data = "Опитвам се да се свържа..."
    st.session_state.ws_started = True
    
    def run_websocket():
        # Добавяме API ключа в Header-а, както изискват повечето професионални API-та
        auth_header = {"Authorization": f"Bearer {st.secrets['BZZOIRO_API_KEY']}"}
        
        def on_message(ws, message):
            st.session_state.live_data = message
            
        def on_error(ws, error):
            st.session_state.live_data = f"Грешка в WebSocket: {error}"

        ws = websocket.WebSocketApp(
            "wss://sports.bzzoiro.com/ws/live/", 
            on_message=on_message,
            on_error=on_error,
            header=auth_header
        )
        ws.run_forever()

    threading.Thread(target=run_websocket, daemon=True).start()

# Показваме данните и бутона
st.write(f"Данни от Bzzoiro: {st.session_state.live_data}")

if st.button("Анализирай мача"):
    try:
        # Gemini анализ
        prompt = f"Анализирай следните данни за залог: {st.session_state.live_data}"
        response = model.generate_content(prompt)
        st.write("### AI Анализ:")
        st.write(response.text)
    except Exception as e:
        st.write(f"Грешка при анализа: {e}")
