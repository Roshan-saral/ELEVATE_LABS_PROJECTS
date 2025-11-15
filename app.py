import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta, timezone

# Firebase imports
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- STREAMLIT PAGE CONFIG ----------------
st.set_page_config(
    page_title="🌎 Global Weather Insights",
    layout="wide",
    page_icon="✨"
)

# --- INLINE CSS FOR PREMIUM DASHBOARD STYLE (The "Liked by Everyone" Look) ---
st.markdown("""
<style>
/* 1. Overall Background and Text */
.main {
    background-color: #0E1117; /* Very Dark Blue/Black */
    color: #F0F2F6; /* Light Off-White Text */
}
/* 2. Custom Card Styling (Sleek, Lifted Effect) */
div[data-testid="stMetric"] > div {
    background-color: #1F2536; /* Slightly lighter card background */
    padding: 20px 25px;
    border-radius: 12px;
    border-left: 5px solid #4BBFE3; /* Modern accent line */
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4); /* Stronger, deeper shadow */
    transition: all 0.3s ease-in-out;
}
div[data-testid="stMetric"] > div:hover {
    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.6); /* Lift effect on hover */
}

/* 3. Metric Value and Label Styling */
div[data-testid="stMetric"] label {
    font-size: 1.1rem;
    color: #B0B0C4; /* Subdued label color */
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 2.2rem; /* Key data emphasis */
    font-weight: 800;
    color: #4BBFE3; /* Highlight color: Aqua Blue */
}

/* 4. Section Headers */
h2 {
    color: #F0F2F6;
    border-bottom: 3px solid #4BBFE3;
    padding-bottom: 10px;
    margin-top: 35px;
    font-weight: 600;
    font-size: 1.7rem;
}
/* 5. Streamlit Info/Success Boxes */
div[data-testid="stAlert"] {
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)
# ---------------- SECRETS & FIREBASE SETUP ----------------
API_KEY = st.secrets["OPENWEATHER_API_KEY"]
firebase_creds = st.secrets["FIREBASE"]

@st.cache_resource
def init_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": firebase_creds["type"],
            "project_id": firebase_creds["project_id"],
            "private_key_id": firebase_creds["private_key_id"],
            "private_key": firebase_creds["private_key"],
            "client_email": firebase_creds["client_email"],
            "client_id": firebase_creds["client_id"],
            "auth_uri": firebase_creds["auth_uri"],
            "token_uri": firebase_creds["token_uri"],
            "auth_provider_x509_cert_url": firebase_creds["auth_provider_x509_cert_url"],
            "client_x509_cert_url": firebase_creds["client_x509_cert_url"]
        })
        # Initialize with name to avoid re-initialization error
        firebase_admin.initialize_app(cred, name='weather_app')
    return firestore.client(firebase_admin.get_app('weather_app'))

db = init_firestore()
weather_collection = db.collection("weather_data")
history_collection = db.collection("weather_history")

# ---------------- SIDEBAR ----------------
st.sidebar.title("🛠️ Global Weather Control")
city = st.sidebar.text_input("Enter City Name", "London")
refresh_interval = st.sidebar.slider("Auto-refresh (minutes)", 5, 30, 10)
st.sidebar.markdown("---")
st.sidebar.markdown("✅ **Source:** OpenWeatherMap API")
st.sidebar.markdown("💾 **Cache:** Firebase Firestore")

# ---------------- FUNCTIONS ----------------
@st.cache_data
def get_current_weather(city_name):
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    response = requests.get("http://api.openweathermap.org/data/2.5/weather", params=params,timeout = None)
    data = response.json()
    if data.get("cod") != 200:
        return None
    weather_info = {
        "city": city_name.title(),
        "temperature": data['main']['temp'],
        "humidity": data['main']['humidity'],
        "wind_speed": data['wind']['speed'],
        "condition": data['weather'][0]['description'].title(),
        "icon": data['weather'][0]['icon'],
        "timestamp": datetime.now(timezone.utc)
    }
    # Store in Firestore (latest + history)
    weather_collection.document(city_name.lower()).set(weather_info)
    history_collection.add(weather_info)
    return weather_info
@st.cache_data
def get_forecast(city_name):
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    response = requests.get("http://api.openweathermap.org/data/2.5/forecast", params=params,timeout = None)
    data = response.json()
    if data.get("cod") != "200":
        return None
    df = pd.DataFrame(data['list'])
    df['dt'] = pd.to_datetime(df['dt'], unit='s')
    df['Temperature'] = df['main'].apply(lambda x: x['temp'])
    df['Humidity'] = df['main'].apply(lambda x: x['humidity'])
    df['Condition'] = df['weather'].apply(lambda x: x[0]['description'])
    return df[['dt', 'Temperature', 'Humidity', 'Condition']]
@st.cache_data
def get_city_coordinates(city_name):
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    response = requests.get(
        "http://api.openweathermap.org/data/2.5/weather",
        params=params,
        timeout=None
    )
    data = response.json()
    if "coord" in data:
        return data["coord"]["lat"], data["coord"]["lon"]
    return None, None

@st.cache_data
def get_historical_data(city_name, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    query = history_collection.where("city", "==", city_name.title()).where("timestamp", ">", cutoff)
    docs = query.stream()
    data = [doc.to_dict() for doc in docs]
    if not data:
        return None
    df = pd.DataFrame(data)
    df = df.sort_values("timestamp")
    df['timestamp'] = df['timestamp'].apply(lambda x: x.astimezone(timezone.utc) if hasattr(x, 'astimezone') else x)
    return df

# ---------------- HEADER ----------------
st.markdown(f"<h1 style='text-align:center; color:#4BBFE3;'>✨ Global Weather Insights Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:#B0B0C4; font-size: 1.2em;'>Monitoring live weather conditions for: **{city.title()}**</p>", unsafe_allow_html=True)
st.markdown("---")

# ---------------- DISPLAY WEATHER ----------------
if city:
    doc = weather_collection.document(city.lower()).get()
    weather = None
    
    if doc.exists:
        weather = doc.to_dict()
        time_diff = datetime.now(timezone.utc) - weather["timestamp"]
        
        if time_diff.total_seconds() > refresh_interval * 60:
            with st.spinner(f"Cached data is old. Fetching fresh weather for {city.title()}..."):
                weather = get_current_weather(city)
            if weather:
                 st.success("✅ New data fetched and cached successfully.")
        else:
            st.info(f"💾 Using cached data. Last update: {weather['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} UTC")
    else:
        with st.spinner(f"Fetching initial weather data for {city.title()}..."):
            weather = get_current_weather(city)
        if weather:
             st.success("✅ Initial data fetched and cached successfully.")


    if weather:
        
        # --- Current Conditions Section ---
        st.markdown("## ☀️ Current Environmental Metrics")
        
        # 4 columns for metrics + 1 column for icon/status
        col1, col2, col3, col4, col5 = st.columns([1, 1.5, 1.5, 1.5, 1.5])
        
        # Icon and Status in a clean column
        with col1:
            icon_url = f"http://openweathermap.org/img/wn/{weather['icon']}@4x.png"
            st.image(icon_url, width=120)
            st.markdown(f"<p style='text-align:center; font-size: 1.3em; font-weight: bold; color: #F0F2F6;'>{weather['condition']}</p>", unsafe_allow_html=True)

        col2.metric("🌡 Temperature (C)", f"{weather['temperature']:.1f} °C")
        col3.metric("💧 Relative Humidity", f"{weather['humidity']} %")
        col4.metric("💨 Wind Velocity", f"{weather['wind_speed']:.1f} m/s")
        col5.metric("Target City", weather['city'])
        
        st.markdown("---")

        # --- Forecast & Historical Data Section ---
        
        st.markdown("## 📊 Forecast & Trend Analysis")

        df_forecast = get_forecast(city)
        df_history = get_historical_data(city, days=7)

        # Use two rows of columns to stack forecast and history charts elegantly
        chart_row1_col1, chart_row1_col2 = st.columns(2)
        chart_row2_col1, chart_row2_col2 = st.columns(2)

        if df_forecast is not None:
            
            # Forecast Temperature
            with chart_row1_col1:
                fig_temp = px.line(df_forecast, x='dt', y='Temperature', title="5-Day Temperature Forecast",
                                   markers=True, template='plotly_dark')
                # Use a gradient-like theme color (Orange for heat)
                fig_temp.update_traces(line=dict(color="#FF7F00", width=4, shape='spline'), mode='lines+markers') 
                fig_temp.update_layout(xaxis_title="Date/Time", yaxis_title="Temp (°C)", hovermode="x unified")
                st.plotly_chart(fig_temp, use_container_width=True)

            # Forecast Humidity
            with chart_row1_col2:
                fig_hum = px.line(df_forecast, x='dt', y='Humidity', title="5-Day Humidity Forecast",
                                 markers=True, template='plotly_dark')
                # Use Aqua Blue (Water)
                fig_hum.update_traces(line=dict(color="#4BBFE3", width=4, shape='spline'), mode='lines+markers') 
                fig_hum.update_layout(xaxis_title="Date/Time", yaxis_title="Humidity (%)", hovermode="x unified")
                st.plotly_chart(fig_hum, use_container_width=True)

        if df_history is not None and not df_history.empty:
            
            # Historical Temperature
            with chart_row2_col1:
                fig_hist_temp = px.line(df_history, x='timestamp', y='temperature',
                                         title="Historical Temperature Trend (7 Days)", markers=True, template='plotly_dark')
                # Use Red/Pink (Historical heat)
                fig_hist_temp.update_traces(line=dict(color="#FF4560", width=4, shape='spline'), mode='lines+markers') 
                fig_hist_temp.update_layout(xaxis_title="Timestamp (UTC)", yaxis_title="Temp (°C)", hovermode="x unified")
                st.plotly_chart(fig_hist_temp, use_container_width=True)

            # Historical Humidity
            with chart_row2_col2:
                fig_hist_hum = px.line(df_history, x='timestamp', y='humidity',
                                       title="Historical Humidity Trend (7 Days)", markers=True, template='plotly_dark')
                # Use Teal/Cyan (Historical water)
                fig_hist_hum.update_traces(line=dict(color="#00CED1", width=4, shape='spline'), mode='lines+markers') 
                fig_hist_hum.update_layout(xaxis_title="Timestamp (UTC)", yaxis_title="Humidity (%)", hovermode="x unified")
                st.plotly_chart(fig_hist_hum, use_container_width=True)
                
        else:
            st.info("No sufficient historical data yet. Check back in a few hours.")

        st.markdown("---")

        # --- Map Section ---
        st.markdown("## 🌍 Geographic Location")
        lat, lon = get_city_coordinates(city)
        
        if lat and lon:
            
            # Center the map visually
            map_col1, map_col2, map_col3 = st.columns([0.5, 3, 0.5])
            
            with map_col2:
                m = folium.Map(location=[lat, lon], zoom_start=11, tiles="cartodbdarkmatter") # Darker map style for elegance
                folium.CircleMarker(
                    [lat, lon], 
                    radius=10,
                    color="#FF7F00",
                    fill=True,
                    fill_color="#FF7F00",
                    popup=f"**{city.title()}**"
                ).add_to(m)
                st_folium(m, width=900, height=450)
        
    else:
        st.error(f"⚠️ Could not retrieve weather data for '{city.title()}'. Please check the city name.")