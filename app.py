import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
import folium
from streamlit_folium import st_folium
import math

# Firebase imports
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- STREAMLIT PAGE CONFIG ----------------
st.set_page_config(
    page_title="🌎 Global Weather Insights",
    layout="wide",
    page_icon="✨"
)

# --- NEW: GOOGLE FONT INTEGRATION & ENHANCED CSS FOR AMAZING UI ---
st.markdown("""
<style>
/* Import a modern, clean font like 'Poppins' or 'Montserrat' */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');

/* 1. Overall Background and Text */
.main {
    background-color: #0E1117; /* Very Dark Blue/Black */
    color: #F0F2F6; /* Light Off-White Text */
    font-family: 'Montserrat', sans-serif; /* Apply new font */
}

/* 2. Custom Header Styles */
h1 {
    font-size: 3em;
    font-weight: 800;
    color: #4BBFE3 !important; /* Primary Accent Color */
    text-shadow: 0 0 10px rgba(75, 191, 227, 0.5); /* Subtle glow */
    padding-top: 10px;
}

/* 3. Section Headers */
h2 {
    color: #F0F2F6;
    border-bottom: 3px solid #4BBFE3;
    padding-bottom: 10px;
    margin-top: 40px; /* Increased top margin for better separation */
    font-weight: 600;
    font-size: 1.8rem;
    font-family: 'Montserrat', sans-serif;
}

/* 4. Custom Card Styling (Sleek, Lifted Effect) */
div[data-testid="stMetric"] > div {
    background-color: #1F2536; /* Slightly lighter card background */
    padding: 25px 30px; /* Increased padding */
    border-radius: 15px; /* More rounded corners */
    border-left: 6px solid #4BBFE3; /* Thicker accent line */
    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.5); /* Stronger shadow */
    transition: all 0.4s ease-in-out; /* Smoother transition */
}
div[data-testid="stMetric"] > div:hover {
    background-color: #283042; /* Darker on hover */
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.7); /* Lift effect on hover */
    transform: translateY(-2px); /* Slight lift */
}

/* 5. Metric Value and Label Styling */
div[data-testid="stMetric"] label {
    font-size: 1.1rem;
    color: #B0B0C4; /* Subdued label color */
    font-weight: 400;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 2.5rem; /* Key data emphasis - Larger */
    font-weight: 800;
    color: #4BBFE3; /* Default Highlight color: Aqua Blue */
    font-family: 'Montserrat', sans-serif;
}

/* Specific Metric Value Theming (Expert Touch) */
/* Temperature */
div[data-testid="stMetric"]:nth-child(2) div[data-testid="stMetricValue"] {
    color: #FF4560; /* Hot Pink/Red for temperature */
}
/* Apparent Temperature */
div[data-testid="stMetric"]:nth-child(3) div[data-testid="stMetricValue"] {
    color: #FFA500; /* Orange for apparent temperature */
}
/* Humidity */
div[data-testid="stMetric"]:nth-child(4) div[data-testid="stMetricValue"] {
    color: #4BBFE3; /* Aqua Blue for humidity/water */
}


/* 6. Sidebar Styling */
.sidebar .sidebar-content {
    background-color: #1F2536;
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SECRETS & FIREBASE SETUP ----------------

try:
    API_KEY = st.secrets["OPENWEATHER_API_KEY"]
except KeyError:
    st.error("🚨 **Configuration Error:** OPENWEATHER_API_KEY not found in `secrets.toml`. Please add it for the app to function.")
    st.stop()
    
try:
    firebase_creds = st.secrets["FIREBASE"]
except KeyError:
    st.error("🚨 **Configuration Error:** FIREBASE secret not found. Cannot connect to Firestore for caching/history.")
    st.stop()


@st.cache_resource
def init_firestore():
    """Initializes and caches the Firestore connection."""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_creds) 
            firebase_admin.initialize_app(cred, name='weather_app')
        
        return firestore.client(firebase_admin.get_app('weather_app'))
    except Exception as e:
        st.error(f"🚨 **Firebase Initialization Error:** {e}")
        st.stop()

db = init_firestore()
weather_collection = db.collection("weather_data")
history_collection = db.collection("weather_history")


# ---------------- UTILITY FUNCTION: ADVANCED METRIC ----------------

def calculate_heat_index(temp_c, rh_percent):
    """
    Calculates the Heat Index (Apparent Temperature) in Celsius.
    Uses the Steadman or Anderson/Rothfusz equation (simplified for C).
    """
    temp_f = (temp_c * 9/5) + 32
    if temp_f < 80:
        return temp_c

    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -6.83783e-03
    c6 = -5.481717e-02
    c7 = 1.22874e-03
    c8 = 8.5282e-04
    c9 = -1.99e-06

    hi_f = (c1 + (c2 * temp_f) + (c3 * rh_percent) + (c4 * temp_f * rh_percent) + 
            (c5 * temp_f**2) + (c6 * rh_percent**2) + (c7 * temp_f**2 * rh_percent) + 
            (c8 * temp_f * rh_percent**2) + (c9 * temp_f**2 * rh_percent**2))
    
    hi_c = (hi_f - 32) * 5/9
    return hi_c

# ---------------- SIDEBAR ----------------
st.sidebar.title("🛠️ Global Weather Control")
city = st.sidebar.text_input("Enter City Name", "London")
refresh_interval = st.sidebar.slider("Auto-refresh (minutes)", 5, 30, 10)
st.sidebar.markdown("---")

current_utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
st.sidebar.markdown(f"**⏰ Current UTC Time:**\n`{current_utc_time}`")

st.sidebar.markdown("---")
st.sidebar.markdown("✅ **Source:** OpenWeatherMap API")
st.sidebar.markdown("💾 **Cache:** Firebase Firestore")

# ---------------- FUNCTIONS ----------------

def get_current_weather(city_name):
    """Fetches current weather, calculates Heat Index, and caches data."""
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    
    try:
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params=params, 
            timeout=10
        )
        response.raise_for_status() 
        data = response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **API Connection Error:** Could not connect to OpenWeatherMap: {e}")
        return None
    
    if data.get("cod") != 200:
        return None
    
    temp_c = data['main']['temp']
    rh = data['main']['humidity']
    heat_index_c = calculate_heat_index(temp_c, rh)

    weather_info = {
        "city": city_name.title(),
        "temperature": temp_c,
        "humidity": rh,
        "wind_speed": data['wind']['speed'],
        "condition": data['weather'][0]['description'].title(),
        "icon": data['weather'][0]['icon'],
        "heat_index": heat_index_c,
        "timestamp": datetime.now(timezone.utc)
    }
    
    weather_collection.document(city_name.lower()).set(weather_info)
    history_collection.add(weather_info)
    return weather_info

@st.cache_data(ttl=timedelta(minutes=15)) # Increased TTL for forecast, as it's less critical than current data
def get_forecast(city_name):
    """Fetches 5-day/3-hour weather forecast."""
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    try:
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/forecast", 
            params=params, 
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ **Forecast API Error:** Could not fetch forecast data: {e}")
        return None

    if data.get("cod") != "200":
        return None
        
    df = pd.DataFrame(data['list'])
    df['dt'] = pd.to_datetime(df['dt'], unit='s', utc=True) 
    df['Temperature'] = df['main'].apply(lambda x: x['temp'])
    df['Humidity'] = df['main'].apply(lambda x: x['humidity'])
    df['Condition'] = df['weather'].apply(lambda x: x[0]['description'])
    return df[['dt', 'Temperature', 'Humidity', 'Condition']]

@st.cache_data(ttl=timedelta(hours=12))
def get_city_coordinates(city_name):
    """Fetches city coordinates."""
    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    try:
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
    except requests.exceptions.RequestException:
        return None, None
        
    if "coord" in data:
        return data["coord"]["lat"], data["coord"]["lon"]
    return None, None

@st.cache_data(ttl=timedelta(minutes=refresh_interval))
def get_historical_data(city_name, days=7):
    """Fetches historical weather data from Firestore for plotting."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days) 
    query = history_collection.where("city", "==", city_name.title()).where("timestamp", ">", cutoff)
    docs = query.stream()
    data = [doc.to_dict() for doc in docs]
    
    if not data:
        return None
        
    df = pd.DataFrame(data)
    df = df.sort_values("timestamp")
    df['timestamp'] = df['timestamp'].apply(lambda x: x.astimezone(timezone.utc) if hasattr(x, 'astimezone') else x)
    df.drop_duplicates(subset=['timestamp'], keep='first', inplace=True) 
    
    return df

# ---------------- HEADER ----------------
# Cleaned up header display for better visual flow
st.markdown(f"<h1 style='text-align:center;'>✨ Global Weather Insights Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:#B0B0C4; font-size: 1.2em;'>**Live Monitoring** for: **{city.title()}**</p>", unsafe_allow_html=True)
st.markdown("---")

# ---------------- DISPLAY WEATHER LOGIC ----------------
if city:
    doc = weather_collection.document(city.lower()).get()
    weather = None
    
    # --- CACHE LOGIC ---
    if doc.exists:
        weather = doc.to_dict()
        time_diff = datetime.now(timezone.utc) - weather["timestamp"] 
        
        if time_diff.total_seconds() > refresh_interval * 60:
            with st.spinner(f"⏳ **Refreshing Data:** Cached data is older than {refresh_interval} mins. Fetching fresh weather..."):
                weather = get_current_weather(city)
            if weather:
                st.toast("✅ New data fetched and cached successfully!", icon='✨')
        else:
            last_update_str = weather['timestamp'].strftime('%H:%M:%S')
            st.info(f"💾 **Cache Active:** Last updated: {last_update_str} UTC. Will refresh in {refresh_interval - time_diff.seconds//60} mins.")
    else:
        with st.spinner(f"🚀 **Initial Fetch:** Retrieving first-time data for {city.title()}..."):
            weather = get_current_weather(city)
        if weather:
            st.toast("✅ Initial data fetched and cached successfully!", icon='🎉')
            
    # ---------------- DISPLAY WEATHER ----------------
    if weather:
        
        # --- Current Conditions Section ---
        st.markdown("## 🌡 Current Environmental Metrics")
        
        # 5 columns for metrics: Icon, Temp, Heat Index, Humidity, Wind
        # Adjusted column widths slightly
        col1, col2, col3, col4, col5 = st.columns([1, 1.3, 1.5, 1.3, 1.3])
        
        # Icon and Status in a unified block
        with col1:
            icon_url = f"http://openweathermap.org/img/wn/{weather['icon']}@4x.png"
            st.image(icon_url, width=120)
            st.markdown(f"<p style='text-align:center; font-size: 1.4em; font-weight: 600; color: #F0F2F6;'>{weather['condition']}</p>", unsafe_allow_html=True)

        col2.metric("🌡 Air Temperature", f"{weather['temperature']:.1f} °C")
        
        # Heat Index Metric
        delta_temp = weather['heat_index'] - weather['temperature']
        col3.metric("🔥 Apparent Temperature", 
                    f"{weather['heat_index']:.1f} °C", 
                    delta=f"{delta_temp:+.1f} °C vs Air Temp", # Explicitly show + or -
                    delta_color="normal")

        col4.metric("💧 Relative Humidity", f"{weather['humidity']} %")
        col5.metric("💨 Wind Velocity", f"{weather['wind_speed']:.1f} m/s")
        
        st.markdown("---")

        # --- Forecast & Historical Data Section ---
        
        st.markdown("## 📈 Forecast & Trend Analysis")

        df_forecast = get_forecast(city)
        df_history = get_historical_data(city, days=7)

        # Use two rows of columns to stack charts
        chart_row1_col1, chart_row1_col2 = st.columns(2)
        chart_row2_col1, chart_row2_col2 = st.columns(2)

        # Plotly Theme Consistency: Use 'plotly_dark' throughout
        
        if df_forecast is not None:
            
            with chart_row1_col1:
                fig_temp = px.line(df_forecast, x='dt', y='Temperature', 
                                   title="5-Day Temperature Forecast", markers=True, 
                                   template='plotly_dark')
                # Use a bold, modern line style
                fig_temp.update_traces(line=dict(color="#FF4560", width=4, shape='spline'), mode='lines+markers') 
                fig_temp.update_layout(xaxis_title="Date/Time (UTC)", yaxis_title="Temp (°C)", hovermode="x unified")
                st.plotly_chart(fig_temp, use_container_width=True)

            with chart_row1_col2:
                fig_hum = px.line(df_forecast, x='dt', y='Humidity', 
                                  title="5-Day Humidity Forecast", markers=True, 
                                  template='plotly_dark')
                fig_hum.update_traces(line=dict(color="#4BBFE3", width=4, shape='spline'), mode='lines+markers') 
                fig_hum.update_layout(xaxis_title="Date/Time (UTC)", yaxis_title="Humidity (%)", hovermode="x unified")
                st.plotly_chart(fig_hum, use_container_width=True)

        if df_history is not None and not df_history.empty:
            
            with chart_row2_col1:
                # Historical Temp & Apparent Temp (Clear Legend Labels)
                fig_hist_temp = px.line(df_history, x='timestamp', 
                                        y=['temperature', 'heat_index'],
                                        title="Historical Temperature Trend (7 Days)", 
                                        markers=True, 
                                        template='plotly_dark')
                
                fig_hist_temp.for_each_trace(lambda t: t.update(name='Apparent Temp (HI)') if t.name == 'heat_index' else t.update(name='Air Temp'))
                fig_hist_temp.update_traces(selector=dict(name='Air Temp'), line=dict(color="#FF4560", width=4, dash='solid'))
                fig_hist_temp.update_traces(selector=dict(name='Apparent Temp (HI)'), line=dict(color="#FFA500", width=2, dash='dot'))

                fig_hist_temp.update_layout(xaxis_title="Timestamp (UTC)", yaxis_title="Temp (°C)", hovermode="x unified", legend_title="")
                st.plotly_chart(fig_hist_temp, use_container_width=True)

            with chart_row2_col2:
                fig_hist_hum = px.line(df_history, x='timestamp', y='humidity',
                                       title="Historical Humidity Trend (7 Days)", 
                                       markers=True, 
                                       template='plotly_dark')
                fig_hist_hum.update_traces(line=dict(color="#00CED1", width=4, shape='spline'), mode='lines+markers') 
                fig_hist_hum.update_layout(xaxis_title="Timestamp (UTC)", yaxis_title="Humidity (%)", hovermode="x unified")
                st.plotly_chart(fig_hist_hum, use_container_width=True)
                
        else:
            st.info("No sufficient historical data yet. Historical data is logged from current weather checks.")

        st.markdown("---")

        # --- Map Section ---
        st.markdown("## 📍 Geographic Location")
        lat, lon = get_city_coordinates(city)
        
        if lat and lon:
            
            # Map Column Centering
            map_col1, map_col2, map_col3 = st.columns([0.5, 3, 0.5])
            
            with map_col2:
                # Use CartoDB Dark Matter for a sleek, dark-mode map style
                m = folium.Map(location=[lat, lon], zoom_start=11, tiles="cartodbdarkmatter") 
                
                # Use a Circle Marker with a clear popup
                folium.CircleMarker(
                    [lat, lon], 
                    radius=15, 
                    color="#FF4560", # Red primary accent
                    fill=True,
                    fill_color="#FF4560",
                    fill_opacity=0.7,
                    popup=f"**{city.title()}**<br>Temp: {weather['temperature']:.1f}°C<br>Condition: {weather['condition']}"
                ).add_to(m)
                
                st_folium(m, width=900, height=450)
        
        else:
            st.warning(f"⚠️ Could not retrieve coordinates for map display for '{city.title()}'.")

    else:
        st.error(f"❌ Could not retrieve **any** weather data for '{city.title()}'. Please check the city name and API configuration.")
