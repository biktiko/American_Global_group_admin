import os
from datetime import datetime
import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# --- Загрузка локальных переменных из .env (для разработки) ---
load_dotenv()

# --- Получение секретов/переменных конфигурации ---
try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
    ACCOUNT_USERNAME = st.secrets["USERNAME"]
    ACCOUNT_PASSWORD = st.secrets["PASSWORD"]
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")
    ACCOUNT_USERNAME = os.getenv("USERNAME")
    ACCOUNT_PASSWORD = os.getenv("PASSWORD")

if not DATABASE_URL or not ACCOUNT_USERNAME or not ACCOUNT_PASSWORD:
    st.error('Не найдены ключевые переменные конфигурации: DATABASE_URL, USERNAME или PASSWORD.')
    st.stop()

st.set_page_config(page_title="AGG Bot Analytics", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

with st.sidebar:
    st.header("Вход в систему")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if username == ACCOUNT_USERNAME and password == ACCOUNT_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный логин или пароль")

if not st.session_state.authenticated:
    st.stop()

@st.cache_data(ttl=300)
def load_data():
    conn = psycopg2.connect(DATABASE_URL)
    users = pd.read_sql("SELECT * FROM users", conn, parse_dates=['created_at'])
    logs = pd.read_sql("SELECT * FROM logs", conn, parse_dates=['created_at'])
    bcs = pd.read_sql("SELECT * FROM broadcasts", conn, parse_dates=['created_at'])
    admins = pd.read_sql("SELECT * FROM admins", conn)
    conn.close()
    return users, logs, bcs, admins

users, logs, broadcasts, admins = load_data()

for df in (users, logs):
    df['day'] = df['created_at'].dt.date
    df['week'] = df['created_at'].dt.to_period('W').apply(lambda r: r.start_time.date())
    df['month'] = df['created_at'].dt.to_period('M').apply(lambda r: r.start_time.date())

broadcasts['recipients_count'] = broadcasts['recipients'].apply(len)
broadcasts['week'] = broadcasts['created_at'].dt.to_period('W').apply(lambda r: r.start_time.date())
broadcasts['month'] = broadcasts['created_at'].dt.to_period('M').apply(lambda r: r.start_time.date())

growth_day = users.groupby('day').size()
growth_week = users.groupby('week').size()
growth_month = users.groupby('month').size()
actions_day = logs.groupby('day').size()
actions_week = logs.groupby('week').size()
actions_month = logs.groupby('month').size()
active_day = logs.groupby('day')['user_id'].nunique()
active_week = logs.groupby('week')['user_id'].nunique()
active_month = logs.groupby('month')['user_id'].nunique()
bcs_sent_week = broadcasts.groupby('week').size()
bcs_sent_month = broadcasts.groupby('month').size()
bcs_recv_week = broadcasts.groupby('week')['recipients_count'].sum()
bcs_recv_month = broadcasts.groupby('month')['recipients_count'].sum()

tab_growth, tab_activity, tab_broadcasts, tab_tables = st.tabs([
    "Рост пользователей", "Активность", "Рассылки", "Таблицы данных"
])

with tab_growth:
    st.header("1. Рост пользователей")
    st.subheader("По дням")
    with st.expander("Данные роста пользователей по дням", expanded=True):
        st.bar_chart(growth_day)
        st.dataframe(growth_day)
    st.subheader("По неделям")
    with st.expander("Данные роста пользователей по неделям", expanded=True):
        st.bar_chart(growth_week)
        st.dataframe(growth_week)
    st.subheader("По месяцам")
    with st.expander("Данные роста пользователей по месяцам", expanded=True):
        st.bar_chart(growth_month)
        st.dataframe(growth_month)

with tab_activity:
    st.header("2–3. Активность бота")
    st.subheader("Взаимодействия в день")
    with st.expander("Данные взаимодействий в день", expanded=True):
        st.line_chart(actions_day)
        st.dataframe(actions_day)
    st.subheader("Уникальные юзеры в день")
    with st.expander("Данные уникальных юзеров в день", expanded=True):
        st.line_chart(active_day)
        st.dataframe(active_day)
    st.subheader("Взаимодействия: неделя / месяц")
    weekly_monthly_actions = pd.DataFrame({
        'неделя': actions_week,
        'месяц': actions_month
    })
    with st.expander("Данные взаимодействий по неделям и месяцам", expanded=True):
        st.line_chart(weekly_monthly_actions)
        st.dataframe(weekly_monthly_actions)
    st.subheader("Уникальные юзеры: неделя / месяц")
    weekly_monthly_active = pd.DataFrame({
        'неделя': active_week,
        'месяц': active_month
    })
    with st.expander("Данные уникальных юзеров по неделям и месяцам", expanded=True):
        st.line_chart(weekly_monthly_active)
        st.dataframe(weekly_monthly_active)

with tab_broadcasts:
    st.header("4–5. Рассылки")
    st.subheader("Рассылок отправлено: неделя / месяц")
    sent_data = pd.DataFrame({
        'неделя': bcs_sent_week,
        'месяц': bcs_sent_month
    })
    with st.expander("Данные отправленных рассылок по неделям и месяцам", expanded=True):
        st.bar_chart(sent_data)
        st.dataframe(sent_data)
    st.subheader("Сообщений доставлено: неделя / месяц")
    recv_data = pd.DataFrame({
        'неделя': bcs_recv_week,
        'месяц': bcs_recv_month
    })
    with st.expander("Данные доставленных сообщений по неделям и месяцам", expanded=True):
        st.bar_chart(recv_data)
        st.dataframe(recv_data)

with tab_tables:
    st.header("Таблицы исходных данных")
    st.subheader("Users")
    st.dataframe(users)
    st.subheader("Logs")
    st.dataframe(logs)
    st.subheader("Broadcasts")
    st.dataframe(broadcasts)
    st.subheader("Admins")
    st.dataframe(admins)
