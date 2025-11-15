import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
import folium
from streamlit_folium import st_folium
import math

# Firebase imports (assuming these are available in your environment)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    # If running outside a Firebase-configured environment, disable DB features
    FIREBASE_AVAILABLE = False


# ---------------- STREAMLIT PAGE CONFIG ----------------
st.set_page_config(
    page_title="🌎 Global Weather Insights",
    layout="wide",
    page_icon="✨"
)

# --- ENHANCED CSS V7.0: Cloud-Native/Telemetry Look ---
st.markdown("""
<style>
/* Import a modern, executive font */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');

/* --- KEYFRAME ANIMATIONS FOR GLOW/PULSE --- */
@keyframes subtle-pulse {
    0% { border-left-color: #00DDEE; box-shadow: 0 0 5px #00DDEE33; } /* Sharper Cyan */
    50% { border-left-color: #00FFFF; box-shadow: 0 0 15px #00FFFF66; } /* Max Glow */
    100% { border-left-color: #00DDEE; box-shadow: 0 0 5px #00DDEE33; }
}

/* 1. Overall Background and Text (Deeper Dark Theme) */
.main {
    background-color: #0A0B0E; /* Even Darker Background (almost black) */
    color: #E6E8ED; /* Light Gray Text */
    font-family: 'Montserrat', sans-serif;
}

/* 2. Custom Header Styles - BIG & NEON GLOW */
h1 {
    font-size: 3.8em;
    font-weight: 800;
    color: #00DDEE !important; /* Primary Accent Color - Sharper Cyan */
    text-align: center;
    /* NEON EFFECT - Multiple shadows for depth and glow */
    text-shadow:
        0 0 10px #00DDEE,
        0 0 20px #00DDEE,
        0 0 40px #00BBDD, 
        0 0 80px #0099BB;
    padding-top: 10px;
    margin-bottom: 0px;
}

/* 3. Section Headers - Clean Separation and Font Consistency */
h2 {
    color: #F0F2F6;
    border-bottom: 2px solid #00DDEE; /* Sharper cyan color for separation */
    padding-bottom: 8px;
    margin-top: 40px;
    font-weight: 600;
    font-size: 1.8rem;
    font-family: 'Montserrat', sans-serif;
}

/* 4. Custom Card Styling (Sleek, Lifted Effect + Animation) */
div[data-testid="stMetric"] > div {
    background-color: #1A1F26; /* Darker card background */
    padding: 20px 25px; 
    border-radius: 10px;
    border-left: 5px solid #00DDEE; /* Base border */
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.7); /* Deeper shadow */
    transition: all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94); /* Smoother transition */
    
    /* ANIMATION: Apply pulse with shadow effect */
    animation: subtle-pulse 6s ease-in-out infinite; /* Slower pulse */
}
div[data-testid="stMetric"] > div:hover {
    background-color: #262D38;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.9), 0 0 25px rgba(0, 221, 238, 0.6); /* Intense glow on hover */
    transform: translateY(-3px); /* More pronounced lift */
}

/* 5. Metric Value and Label Styling */
div[data-testid="stMetric"] label {
    font-size: 1.0rem;
    color: #A0A5AD; /* Slightly brighter label text */
    font-weight: 400;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 2.2rem;
    font-weight: 800;
    color: #FFFFFF; /* Metric value is now white/neutral, letting the dynamic color from the border and chart lines dominate */
    font-family: 'Montserrat', sans-serif;
}

/* Dynamic Metric Coloring (The "Tears" Factor) - Targeting specific metric index */
/* Temperature: Red */
div[data-testid="stMetric"]:nth-child(1) div[data-testid="stMetricValue"] { color: #FF4560; }
/* Apparent Temperature: Orange */
div[data-testid="stMetric"]:nth-child(2) div[data-testid="stMetricValue"] { color: #FFA500; }
/* Humidity: Aqua Blue */
div[data-testid="stMetric"]:nth-child(3) div[data-testid="stMetricValue"] { color: #00DDEE; }
/* Wind: Teal */
div[data-testid="stMetric"]:nth-child(4) div[data-testid="stMetricValue"] { color: #00CED1; }

/* Styling for Expander/Flashcard Detail area */
.streamlit-expanderHeader {
    background-color: #151921 !important;
    border-radius: 8px;
    font-weight: 600 !important;
    color: #F0F2F6 !important;
    border: 1px solid #2C3545; /* Sharper outline */
}

/* 6. Sidebar Styling */
.sidebar .sidebar-content {
    background-color: #1A1F26;
    padding: 20px;
}

/* 7. Cloud-Native Status Bar Styling */
.status-bar {
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 12px 0;
    margin-top: 20px;
    margin-bottom: 25px;
    background-color: #1A1F26;
    border: 1px solid #2C3545;
    border-radius: 8px;
    font-size: 0.95em;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.5);
}
.status-item {
    text-align: center;
    padding: 0 10px;
    color: #B0B0C4;
}
.status-item strong {
    color: #00DDEE; /* Cyan highlight for status names */
    font-weight: 600;
}
.status-item .active {
    color: #4CAF50; /* Green for Active */
    font-weight: 800;
}
.status-item .disabled {
    color: #F44336; /* Red for Disabled */
    font-weight: 800;
}
.status-item .warning {
    color: #FFC107; /* Yellow for Warning/Missing data */
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SECRETS & FIREBASE SETUP ----------------

API_KEY = ""
db = None

try:
    # IMPORTANT: Replace these with your actual secrets or run with a secrets.toml file
    # If running locally, you must provide these keys in .streamlit/secrets.toml
    API_KEY = st.secrets.get("OPENWEATHER_API_KEY", "YOUR_OPENWEATHER_API_KEY")
    firebase_creds = st.secrets.get("FIREBASE", {})
    
    if FIREBASE_AVAILABLE and firebase_creds and firebase_creds.get("project_id"):
        @st.cache_resource
        def init_firestore():
            """Initializes and caches the Firestore connection."""
            try:
                if not firebase_admin._apps:
                    # Safely create credential from dictionary
                    cred = credentials.Certificate({
                        "type": firebase_creds["type"],
                        "project_id": firebase_creds["project_id"],
                        "private_key_id": firebase_creds["private_key_id"],
                        "private_key": firebase_creds["private_key"].replace('\\n', '\n'),
                        "client_email": firebase_creds["client_email"],
                        "client_id": firebase_creds["client_id"],
                        "auth_uri": firebase_creds["auth_uri"],
                        "token_uri": firebase_creds["token_uri"],
                        "auth_provider_x509_cert_url": firebase_creds["auth_provider_x509_cert_url"],
                        "client_x509_cert_url": firebase_creds["client_x509_cert_url"]
                    })
                    firebase_admin.initialize_app(cred, name='weather_app')
                
                return firestore.client(firebase_admin.get_app('weather_app'))
            except Exception as e:
                st.error(f"🚨 **Firebase Init Error:** Could not connect. History/Caching disabled. Error: {e}")
                return None

        db = init_firestore()
        if db:
            weather_collection = db.collection("weather_data")
            history_collection = db.collection("weather_history")
            st.session_state['db_status'] = 'Active'
    else:
        st.session_state['db_status'] = 'Disabled (Missing Config or Dependencies)'

except Exception as e:
    st.session_state['db_status'] = f'Disabled (Secrets Error: {type(e).__name__})'


# ---------------- UTILITY FUNCTION: APPARENT TEMPERATURE ----------------

def calculate_heat_index(temp_c, rh_percent):
    """
    Calculates the Heat Index (Apparent Temperature) in Celsius.
    Uses the NOAA simplified formula.
    """
    temp_f = (temp_c * 9/5) + 32
    if temp_f < 80: # Heat Index only applies when temp >= 80F (26.7C)
        return temp_c

    # NOAA Simplified HI formula (requires F and RH as percent for simplified coeffs)
    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -6.83783e-03
    c6 = -5.481717e-02
    c7 = 1.22874e-03
    c8 = 8.5282e-04
    c9 = -1.99e-06
    
    rh = rh_percent # RH is used as percent in this formula
    
    hi_f = (c1 + (c2 * temp_f) + (c3 * rh) + (c4 * temp_f * rh) + 
            (c5 * temp_f**2) + (c6 * rh**2) + (c7 * temp_f**2 * rh) + 
            (c8 * temp_f * rh**2) + (c9 * temp_f**2 * rh**2))
    
    hi_c = (hi_f - 32) * 5/9
    return hi_c

# ---------------- SIDEBAR ----------------
st.sidebar.title("🛠️ Global Weather Control")
city = st.sidebar.text_input("Enter City Name", "London")
refresh_interval = st.sidebar.slider("Auto-refresh (minutes)", 5, 30, 10)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**⏰ Current UTC Time:**\n`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`")
st.sidebar.markdown("---")
st.sidebar.markdown("✅ **Source:** OpenWeatherMap API")
st.sidebar.markdown(f"💾 **Cache:** Firebase Firestore ({st.session_state.get('db_status', 'Initializing...')})")

# ---------------- CORE DATA FUNCTIONS ----------------

def get_current_weather(city_name):
    """Fetches current weather, calculates Heat Index, and caches data."""
    if API_KEY == "YOUR_OPENWEATHER_API_KEY":
        st.error("❌ **Configuration Error:** Please set a valid OpenWeatherMap API key.")
        return None
        
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
        st.error(f"❌ API Response Error: {data.get('message', 'City not found')}")
        return None
    
    temp_c = data['main']['temp']
    rh = data['main']['humidity']
    
    # Calculate Apparent Temperature
    heat_index_c = calculate_heat_index(temp_c, rh)

    weather_info = {
        "city": city_name.title(),
        "temperature": temp_c,
        "humidity": rh,
        "wind_speed": data['wind']['speed'],
        "condition": data['weather'][0]['description'].title(),
        "icon": data['weather'][0]['icon'],
        "heat_index": heat_index_c, 
        "timestamp": datetime.now(timezone.utc),
        "lat": data['coord']['lat'],
        "lon": data['coord']['lon']
    }
    
    # Store in Firestore (latest + history)
    if db:
        try:
            weather_collection.document(city_name.lower()).set(weather_info)
            history_collection.add(weather_info)
        except Exception as e:
             st.warning(f"⚠️ Failed to save data to Firestore: {e}")
            
    return weather_info

@st.cache_data(ttl=timedelta(minutes=refresh_interval * 3)) # Longer TTL for forecast
def get_forecast(city_name):
    """Fetches 5-day/3-hour weather forecast."""
    if API_KEY == "YOUR_OPENWEATHER_API_KEY": return None

    params = {"q": city_name, "appid": API_KEY, "units": "metric"}
    try:
        response = requests.get("http://api.openweathermap.org/data/2.5/forecast", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return None

    if data.get("cod") != "200":
        return None
        
    df = pd.DataFrame(data['list'])
    df['dt'] = pd.to_datetime(df['dt'], unit='s', utc=True)
    df['Temperature'] = df['main'].apply(lambda x: x['temp'])
    df['Humidity'] = df['main'].apply(lambda x: x['humidity'])
    df['Condition'] = df['weather'].apply(lambda x: x[0]['description'])
    return df[['dt', 'Temperature', 'Humidity', 'Condition']]

@st.cache_data(ttl=timedelta(minutes=refresh_interval))
def get_historical_data(city_name, days=7):
    """Fetches historical weather data from Firestore for plotting."""
    if not db: return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        query = history_collection.where("city", "==", city_name.title()).where("timestamp", ">", cutoff)
        docs = query.stream()
        data = [doc.to_dict() for doc in docs]
        
        if not data:
            return None
            
        df = pd.DataFrame(data)
        df = df.sort_values("timestamp")
        # Ensure timestamp is tz-aware and sortable
        df['timestamp'] = df['timestamp'].apply(lambda x: x.astimezone(timezone.utc) if hasattr(x, 'astimezone') else pd.to_datetime(x).tz_convert(timezone.utc))
        # Remove duplicate timestamps for clean line plotting
        df.drop_duplicates(subset=['timestamp'], keep='first', inplace=True) 
        return df
    except Exception as e:
        st.error(f"❌ Failed to fetch historical data: {e}")
        return None

# ---------------- PLOTLY CONFIG (Reusable) ----------------
# Added transition_duration for smooth updates (animation effect)
PLOTLY_CONFIG = dict(
    xaxis_title="Date/Time (UTC)", 
    yaxis_title="Value", 
    hovermode="x unified", 
    legend_title="", 
    template='plotly_dark',
    transition_duration=500 # Smooth transition for updates
)

# ---------------- DISPLAY FUNCTIONS (Cleaned Modules) ----------------

def display_status_bar(city, refresh_interval, db_status, api_key_set):
    """Displays a cloud-native style status bar for key service checks."""
    
    # Determine Status Colors/Emojis
    db_status_text = db_status.split(' ')[0]
    db_color = "active" if db_status_text == 'Active' else "warning"
    api_key_set = API_KEY != "YOUR_OPENWEATHER_API_KEY"
    api_color = "active" if api_key_set else "disabled"
    
    api_icon = "🟢" if api_key_set else "🔴"
    db_icon = "🟢" if db_status_text == 'Active' else "🟡"
    
    # Build HTML for the status bar
    status_html = f"""
    <div class="status-bar">
        <div class="status-item">
            <strong>API Status:</strong> <span class='{api_color}'>{api_icon} {'Active' if api_key_set else 'Missing Key'}</span>
        </div>
        <div class="status-item">
            <strong>Database Cache:</strong> <span class='{db_color}'>{db_icon} {db_status_text}</span>
        </div>
        <div class="status-item">
            <strong>Target City:</strong> <span>📍 {city.title()}</span>
        </div>
        <div class="status-item">
            <strong>Refresh Rate:</strong> <span>🔄 {refresh_interval} mins</span>
        </div>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)


def display_current_metrics(weather, df_history, city):
    """Displays the current weather status, icon, and the four key metric cards (Flash Cards)."""
    st.markdown("## ☀️ Current Environmental Metrics & Drilldown")
    
    col_status, col_cards = st.columns([1, 4])
    
    # Icon and Status
    with col_status:
        icon_url = f"http://openweathermap.org/img/wn/{weather['icon']}@4x.png"
        st.image(icon_url, width=150) 
        st.markdown(f"<p style='text-align:center; font-size: 1.6em; font-weight: 800; color: #E6E8ED;'>{weather['condition']}</p>", unsafe_allow_html=True)

    # Metrics Column (Flashcards)
    col_card_1, col_card_2, col_card_3, col_card_4 = col_cards.columns(4)
    
    # CARD 1: Air Temperature
    with col_card_1:
        st.metric("🌡 Air Temperature", f"{weather['temperature']:.1f} °C")
        with st.expander("Show 24h Trend"):
            if df_history is not None and not df_history.empty:
                df_24h = df_history[df_history['timestamp'] >= datetime.now(timezone.utc) - timedelta(hours=24)]
                if not df_24h.empty:
                    try:
                        fig_mini = px.line(df_24h, x='timestamp', y='temperature', 
                                        height=200, template='plotly_dark')
                        # Ensure transition is applied
                        fig_mini.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20), 
                                            xaxis_title=None, yaxis_title=None, transition_duration=500)
                        fig_mini.update_traces(line=dict(color="#FF4560", width=3, shape='spline'))
                        st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False})
                    except Exception as e:
                        st.caption(f"Error plotting 24h trend: {e}")
                else:
                    st.caption("Not enough data points in the last 24 hours.")
            else:
                st.caption("Not enough history for 24h trend.")

    # CARD 2: Apparent Temp
    with col_card_2:
        delta_temp = weather['heat_index'] - weather['temperature']
        st.metric("🔥 Apparent Temp", 
                    f"{weather['heat_index']:.1f} °C", 
                    delta=f"{delta_temp:+.1f} °C vs Air Temp", 
                    delta_color="normal")
        with st.expander("What is Apparent Temp?"):
            st.markdown("**Feels Like:** This metric is the Heat Index, which shows what the temperature *feels* like when considering high humidity. It's an important measure of thermal comfort and health risk.")
            st.markdown(f"**Current Humidity Factor:** {weather['humidity']} %")

    # CARD 3: Humidity
    with col_card_3:
        st.metric("💧 Relative Humidity", f"{weather['humidity']} %")
        with st.expander("Humidity Analysis"):
            st.markdown(f"**Saturation:** The air currently holds {weather['humidity']}% of the maximum moisture it can hold at this temperature. High values lead to muggy conditions.")
            st.markdown("Relative Humidity is key for predicting fog, dew, and precipitation risk.")

    # CARD 4: Wind
    with col_card_4:
        wind_kmh = weather['wind_speed'] * 3.6
        st.metric("💨 Wind Velocity", f"{weather['wind_speed']:.1f} m/s")
        with st.expander("Wind Details"):
            st.markdown(f"**Speed:** {wind_kmh:.1f} km/h")
            st.markdown(f"**Classification:** Light to Moderate Breeze (depending on speed).")
    
    st.markdown("---")

def display_forecast_charts(df_forecast, plot_config):
    """Displays 5-day forecast charts (Temperature, Humidity, and 3D plot with tilting)."""
    st.markdown("## 📊 Forecast & Trend Analysis")
    
    if df_forecast is not None and not df_forecast.empty: 
        chart_row1_col1, chart_row1_col2 = st.columns(2)
        
        # --- Temperature Chart ---
        try:
            with chart_row1_col1:
                fig_temp = px.line(df_forecast, x='dt', y='Temperature', title="5-Day Temperature Forecast", markers=True)
                fig_temp.update_traces(line=dict(color="#FF4560", width=4, shape='spline'), mode='lines+markers') 
                # FIX 1: Apply generic config first, then update yaxis title separately
                fig_temp.update_layout(**plot_config)
                fig_temp.update_yaxes(title_text="Temp (°C)")
                st.plotly_chart(fig_temp, use_container_width=True)
        except Exception as e:
            st.error(f"Error plotting Temperature Forecast: {e}")

        # --- Humidity Chart ---
        try:
            with chart_row1_col2:
                fig_hum = px.line(df_forecast, x='dt', y='Humidity', title="5-Day Humidity Forecast", markers=True)
                fig_hum.update_traces(line=dict(color="#00DDEE", width=4, shape='spline'), mode='lines+markers') 
                # FIX 2: Apply generic config first, then update yaxis title separately
                fig_hum.update_layout(**plot_config)
                fig_hum.update_yaxes(title_text="Humidity (%)")
                st.plotly_chart(fig_hum, use_container_width=True)
        except Exception as e:
            st.error(f"Error plotting Humidity Forecast: {e}")

        # --- 3D Visualization Section (Tilting) ---
        st.markdown("## 🌪 3D Forecast Space: Temp, Humidity, and Time")
        try:
            # Prepare the data: Use a numeric representation of time for the X axis
            start_time = df_forecast['dt'].min()
            df_forecast['Time_Hours'] = (df_forecast['dt'] - start_time).dt.total_seconds() / 3600
            
            # Create a 3D Scatter Plot (This supports interactive tilting!)
            fig_3d = px.scatter_3d(
                df_forecast, 
                x='Time_Hours', 
                y='Temperature', 
                z='Humidity',
                color='Temperature',
                size='Humidity',
                title='5-Day Forecast Visualization (Time vs Temp vs Humidity)',
                labels={'Time_Hours': 'Time (Hours from Start)', 'Temperature': 'Temp (°C)', 'Humidity': 'Humidity (%)'},
                template='plotly_dark',
                height=700
            )
            
            # Apply transition duration to 3D plot as well
            fig_3d.update_layout(transition_duration=500,
                scene=dict(
                    xaxis_title='Time (Hours)',
                    yaxis_title='Temperature (°C)',
                    zaxis_title='Humidity (%)',
                    camera=dict(
                        up=dict(x=0, y=0, z=1), 
                        center=dict(x=0, y=0, z=0), 
                        eye=dict(x=1.5, y=1.5, z=1.5)
                    )
                )
            )

            st.plotly_chart(fig_3d, use_container_width=True)
        except Exception as e:
            st.error(f"Error plotting 3D Forecast: {e}")

    else:
        st.info("No forecast data available to display charts.")
    
    st.markdown("---")

def display_historical_trends(df_history, plot_config):
    """Displays historical data charts with sparse data handling and transitions."""
    st.markdown("## 📈 Historical Trend (Past 7 Days)")

    if df_history is not None and not df_history.empty:
        
        # --- SPARSE DATA HANDLER: Now uses st.status for animation ---
        # Check if we have very few data points (e.g., less than 10)
        if len(df_history) < 10:
             # Using st.status with state='running' provides a native, spinning animation
             with st.status("⏳ **Data Collection Active**", expanded=True) as status:
                st.markdown("💡 **Sparse Data Alert:** The historical trend below currently has **fewer than 10 logged data points**.")
                st.markdown("We're actively **collecting new data points** from the API every 10 minutes.")
                st.markdown("Trend lines may appear **choppy or vertical** until more data is accumulated over time.")
                # Ensure the status icon is always spinning while data is sparse
                status.update(label="⏳ **Data Collection Active**", state="running")
        
        h_col1, h_col2 = st.columns(2)
        
        # --- Historical Temperature Chart ---
        try:
            with h_col1:
                fig_hist_temp = px.line(df_history, x='timestamp', y=['temperature', 'heat_index'],
                                            title="Historical Air Temp vs. Apparent Temp", markers=True)
                
                # Naming traces for clarity
                fig_hist_temp.for_each_trace(lambda t: t.update(name='Apparent Temp (HI)') if t.name == 'heat_index' else t.update(name='Air Temp'))
                fig_hist_temp.update_traces(selector=dict(name='Air Temp'), line=dict(color="#FF4560", width=4, dash='solid', shape='spline'))
                fig_hist_temp.update_traces(selector=dict(name='Apparent Temp (HI)'), line=dict(color="#FFA500", width=2, dash='dot', shape='spline'))

                # FIX 3: Apply generic config first, then update yaxis title separately
                fig_hist_temp.update_layout(**plot_config)
                fig_hist_temp.update_yaxes(title_text="Temp (°C)")
                st.plotly_chart(fig_hist_temp, use_container_width=True)
        except Exception as e:
            st.error(f"Error plotting Historical Temperature: {e}")

        # --- Historical Humidity Chart ---
        try:
            with h_col2:
                fig_hist_hum = px.line(df_history, x='timestamp', y='humidity',
                                            title="Historical Humidity Trend", markers=True)
                fig_hist_hum.update_traces(line=dict(color="#00CED1", width=4, shape='spline'), mode='lines+markers') 
                # FIX 4: Apply generic config first, then update yaxis title separately
                fig_hist_hum.update_layout(**plot_config)
                fig_hist_hum.update_yaxes(title_text="Humidity (%)")
                st.plotly_chart(fig_hist_hum, use_container_width=True)
        except Exception as e:
            st.error(f"Error plotting Historical Humidity: {e}")
            
    elif db:
        st.info("No sufficient historical data yet. Data logging began with the first successful fetch.")
    else:
        st.warning("Historical data is unavailable because the Firebase database is disabled.")
    
    st.markdown("---")


def display_map(weather):
    """Displays the city location on a Folium map."""
    st.markdown("## 📍 Geographic Location")
    
    lat, lon = weather['lat'], weather['lon']
    
    map_col1, map_col2, map_col3 = st.columns([0.5, 3, 0.5])
    
    with map_col2:
        m = folium.Map(location=[lat, lon], zoom_start=11, tiles="cartodbdarkmatter") 
        
        folium.CircleMarker(
            [lat, lon], 
            radius=15, 
            color="#FF4560", 
            fill=True,
            fill_color="#FF4560",
            fill_opacity=0.7,
            popup=f"**{weather['city']}**<br>Temp: {weather['temperature']:.1f}°C"
        ).add_to(m)
        
        st_folium(m, width=900, height=450)
    
    st.markdown("---")


# ---------------- MAIN APPLICATION LOGIC ----------------

# H1 is styled with neon effect in the CSS block
st.markdown(f"<h1>✨ Global Weather Insights Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center;color:#B0B0C4; font-size: 1.2em;'>**Live Monitoring Interface**</p>", unsafe_allow_html=True)


api_key_set = API_KEY != "YOUR_OPENWEATHER_API_KEY"
display_status_bar(city, refresh_interval, st.session_state.get('db_status', 'Initializing...'), api_key_set)


if city:
    weather = None
    
    # --- 1. Data Retrieval Logic (Cache/Fetch) ---
    if db:
        doc = weather_collection.document(city.lower()).get()
        
        if doc.exists:
            weather = doc.to_dict()
            # Handle possible datetime conversion if stored as Firestore Timestamp object
            if isinstance(weather["timestamp"], firebase_admin.firestore.datetime.datetime):
                weather["timestamp"] = weather["timestamp"].astimezone(timezone.utc)

            time_diff = datetime.now(timezone.utc) - weather["timestamp"]
            
            if time_diff.total_seconds() > refresh_interval * 60:
                with st.spinner(f"⏳ **Refreshing Data:** Cached data is old. Fetching fresh weather..."):
                    weather = get_current_weather(city)
                if weather:
                    st.success("✅ New data fetched and cached successfully.")
            else:
                last_update_str = weather['timestamp'].strftime('%H:%M:%S')
                st.info(f"💾 **Cache Active:** Last update: {last_update_str} UTC. Next refresh in {refresh_interval - time_diff.seconds//60} mins.")
        else:
            with st.spinner(f"🚀 **Initial Fetch:** Retrieving first-time data for {city.title()}..."):
                weather = get_current_weather(city)
            if weather:
                st.success("✅ Initial data fetched and cached successfully.")
    else:
        # No DB Logic (Direct Fetch)
        with st.spinner(f"🌐 **Live Fetch:** Retrieving real-time data for {city.title()}..."):
            weather = get_current_weather(city)
        if weather:
            st.warning("⚠️ Database disabled. Showing live data without history or persistent caching.")

    # --- 2. Display Components ---
    if weather:
        df_history = get_historical_data(city, days=7)
        df_forecast = get_forecast(city)

        # Execute display functions
        display_current_metrics(weather, df_history, city)
        display_forecast_charts(df_forecast, PLOTLY_CONFIG)
        display_historical_trends(df_history, PLOTLY_CONFIG)
        display_map(weather)
        
    else:
        st.error(f"❌ **Data Retrieval Failed:** Could not retrieve weather data for '{city.title()}'. Check API key and city name.")
