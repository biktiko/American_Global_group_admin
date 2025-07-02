# app.py
import os
from datetime import datetime
import psycopg2
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
ACCOUNT_USERNAME = os.getenv("USERNAME")
ACCOUNT_PASSWORD = os.getenv("PASSWORD")

# Конфигурация страницы
st.set_page_config(page_title="AGG Bot Analytics", layout="wide")

# --- Аутентификация пользователя ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

with st.sidebar:
    st.header("Вход в систему")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if username == ACCOUNT_USERNAME and password == ACCOUNT_PASSWORD:
            st.session_state.authenticated = True
            st.experimental_rerun()
        else:
            st.error("Неверный логин или пароль")

# Остановка показа дашборда, если не аутентифицирован
if not st.session_state.authenticated:
    st.stop()

# --- Загрузка данных из БД ---
@st.cache_data(ttl=300)
def load_data():
    conn = psycopg2.connect(DATABASE_URL)
    users = pd.read_sql("SELECT created_at FROM users", conn, parse_dates=['created_at'])
    logs = pd.read_sql("SELECT created_at, user_id FROM logs", conn, parse_dates=['created_at'])
    bcs = pd.read_sql("SELECT created_at, recipients FROM broadcasts", conn, parse_dates=['created_at'])
    conn.close()
    return users, logs, bcs

users, logs, broadcasts = load_data()

# --- Подготовка дат и вычисление метрик ---
for df in (users, logs):
    df['day']   = df['created_at'].dt.date
    df['week']  = df['created_at'].dt.to_period('W').apply(lambda r: r.start_time.date())
    df['month'] = df['created_at'].dt.to_period('M').apply(lambda r: r.start_time.date())

broadcasts['recipients_count'] = broadcasts['recipients'].apply(len)
broadcasts['week']  = broadcasts['created_at'].dt.to_period('W').apply(lambda r: r.start_time.date())
broadcasts['month'] = broadcasts['created_at'].dt.to_period('M').apply(lambda r: r.start_time.date())

# 1. Рост пользователей
growth_day   = users.groupby('day').size()
growth_week  = users.groupby('week').size()
growth_month = users.groupby('month').size()

# 2. Взаимодействия с ботом
actions_day   = logs.groupby('day').size()
actions_week  = logs.groupby('week').size()
actions_month = logs.groupby('month').size()

# 3. Уникальные активные пользователи
active_day   = logs.groupby('day')['user_id'].nunique()
active_week  = logs.groupby('week')['user_id'].nunique()
active_month = logs.groupby('month')['user_id'].nunique()

# 4. Broadcasts от админов
bcs_sent_week  = broadcasts.groupby('week').size()
bcs_sent_month = broadcasts.groupby('month').size()

# 5. Сообщения доставлено (recipients_count)
bcs_recv_week  = broadcasts.groupby('week')['recipients_count'].sum()
bcs_recv_month = broadcasts.groupby('month')['recipients_count'].sum()

# --- Отображение в табах ---
tab_growth, tab_activity, tab_broadcasts, tab_tables = st.tabs([
    "Рост пользователей", "Активность", "Рассылки", "Таблицы данных"
])

with tab_growth:
    st.header("1. Рост пользователей")
    st.subheader("По дням")
    st.bar_chart(growth_day)
    st.subheader("По неделям")
    st.bar_chart(growth_week)
    st.subheader("По месяцам")
    st.bar_chart(growth_month)

with tab_activity:
    st.header("2–3. Активность бота")
    st.subheader("Взаимодействия в день")
    st.line_chart(actions_day)
    st.subheader("Уникальные юзеры в день")
    st.line_chart(active_day)
    st.subheader("Взаимодействия: неделя / месяц")
    st.line_chart(pd.concat([actions_week, actions_month], axis=1)
                               .rename(columns={0: 'неделя', 1: 'месяц'}))
    st.subheader("Уникальные юзеры: неделя / месяц")
    st.line_chart(pd.concat([active_week, active_month], axis=1)
                               .rename(columns={0: 'неделя', 1: 'месяц'}))

with tab_broadcasts:
    st.header("4–5. Рассылки")
    st.subheader("Broadcasts sent: неделя / месяц")
    st.bar_chart(pd.concat([bcs_sent_week, bcs_sent_month], axis=1)
                              .rename(columns={0: 'неделя', 1: 'месяц'}))
    st.subheader("Сообщений доставлено: неделя / месяц")
    st.bar_chart(pd.concat([bcs_recv_week, bcs_recv_month], axis=1)
                              .rename(columns={0: 'неделя', 1: 'месяц'}))

with tab_tables:
    st.header("Таблицы исходных данных")
    st.subheader("Users")
    st.dataframe(users)
    st.subheader("Logs")
    st.dataframe(logs)
    st.subheader("Broadcasts")
    st.dataframe(broadcasts)
