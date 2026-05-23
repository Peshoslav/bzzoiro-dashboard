import streamlit as st
import pandas as pd
import requests

# Настройка на страницата
st.set_page_config(page_title="Bzzoiro Dashboard", layout="wide")

st.title("📊 Спортно табло в реално време")

# Извличане на API ключа от защитените настройки (Secrets)
# Това ще работи, след като добавите ключа в Streamlit Cloud
try:
    api_key = st.secrets["BZZOIRO_API_KEY"]
except:
    st.warning("API ключът не е намерен в настройките (Secrets).")
    api_key = None

st.write("Добре дошли във вашето автоматизирано табло.")

# Проверка дали API ключът е наличен
if api_key:
    st.success("API ключът е зареден успешно!")
    # Тук по-късно ще добавим логиката за извличане на данни
else:
    st.info("Моля, добавете вашия BZZOIRO_API_KEY в секция Secrets на Streamlit Cloud.")

# Място за бъдещата таблица с данни
st.subheader("Спортни събития")
if st.button("Тествай връзката"):
    st.write("Предстои свързване към Bzzoiro API...")
