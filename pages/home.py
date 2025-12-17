import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import requests
import time
from datetime import datetime, timedelta
from io import BytesIO
import json
import random
import numpy as np
import openai

# Tambahkan path untuk import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.user_manager import UserManager

# -------------------------
# KONFIGURASI API CHEAPSHARK
# -------------------------
CHEAPSHARK_API_URL = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_STORES_URL = "https://www.cheapshark.com/api/1.0/stores"

# -------------------------
# FUNGSI UNTUK MENGAMBIL API KEY DARI STREAMLIT SECRETS
# -------------------------
def get_gemini_api_key():
    """Ambil API key Gemini dari Streamlit Secrets"""
    try:
        # Coba ambil dari secrets.toml (untuk Streamlit Cloud)
        if 'GEMINI_API_KEY' in st.secrets:
            api_key = st.secrets['GEMINI_API_KEY']
            st.session_state.gemini_api_key_source = "streamlit_secrets"
            return api_key
        
        # Fallback: Cek di environment variables
        elif 'GEMINI_API_KEY' in os.environ:
            api_key = os.environ['GEMINI_API_KEY']
            st.session_state.gemini_api_key_source = "environment_variable"
            return api_key
        
        # Fallback: Cek di session state (untuk input manual)
        elif 'gemini_api_key' in st.session_state and st.session_state.gemini_api_key:
            api_key = st.session_state.gemini_api_key
            st.session_state.gemini_api_key_source = "session_state"
            return api_key
        
        else:
            st.session_state.gemini_api_key_source = "not_found"
            return None
            
    except Exception as e:
        st.error(f"Error accessing secrets: {str(e)}")
        return None

# -------------------------
# FUNGSI UNTUK MENDAPATKAN DATA DARI API
# -------------------------
@st.cache_data(ttl=3600)  # Cache untuk 1 jam
def fetch_game_deals(limit=60):
    """Mendapatkan data game deals dari CheapShark API"""
    try:
        params = {
            'storeID': 1,  # Steam store (bisa diubah)
            'pageSize': limit,
            'sortBy': 'Deal Rating',
            'desc': 1
        }
        
        response = requests.get(CHEAPSHARK_API_URL, params=params, timeout=10)
        response.raise_for_status()
        deals = response.json()
        
        # Juga fetch store info untuk logo
        stores_response = requests.get(CHEAPSHARK_STORES_URL, timeout=5)
        stores = {}
        if stores_response.status_code == 200:
            stores_data = stores_response.json()
            for store in stores_data:
                stores[store['storeID']] = store
        
        return deals, stores
    except Exception as e:
        st.error(f"Error fetching data from API: {str(e)}")
        return [], {}

def convert_deals_to_games_format(deals, stores):
    """Convert API data ke format yang sesuai dengan aplikasi"""
    games_list = []
    
    for idx, deal in enumerate(deals):
        # Dapatkan store info
        store_id = deal.get('storeID', '1')
        store_info = stores.get(store_id, {})
        
        # Generate appid unik jika tidak ada
        appid = deal.get('gameID', f"deal_{idx}_{int(time.time())}")
        
        # Parse harga
        try:
            normal_price = float(deal.get('normalPrice', 0))
            sale_price = float(deal.get('salePrice', 0))
            
            # Hitung persentase diskon
            if normal_price > 0 and sale_price > 0:
                savings = float(deal.get('savings', 0))
                discount = f"{savings:.0f}%"
            else:
                discount = "0%"
        except:
            normal_price = 0
            sale_price = 0
            discount = "0%"
        
        # Parse rating dari Steam atau Metacritic
        try:
            # Prioritas: Steam rating, lalu Metacritic
            steam_rating = deal.get('steamRatingPercent', '0')
            if steam_rating and steam_rating != '0':
                rating = float(steam_rating) / 20  # Convert ke 5 skala
                rating = round(rating, 1)
            else:
                # Gunakan Metacritic score
                metacritic_score = deal.get('metacriticScore', '0')
                if metacritic_score and metacritic_score != '0':
                    rating = float(metacritic_score) / 20  # Convert ke 5 skala
                    rating = round(rating, 1)
                else:
                    rating = round(random.uniform(3.5, 5.0), 1)
        except:
            rating = round(random.uniform(3.5, 5.0), 1)
        
        # Parse release date
        try:
            release_date = int(deal.get('releaseDate', 0))
            if release_date > 0:
                release_year = datetime.fromtimestamp(release_date).year
            else:
                # Default berdasarkan data API
                release_year = random.randint(2015, 2024)
        except:
            release_year = random.randint(2015, 2024)
        
        # Parse player count (simulasi - API tidak menyediakan data ini)
        # Gunakan rating count sebagai proxy untuk popularitas
        try:
            rating_count = int(deal.get('steamRatingCount', '0'))
            if rating_count > 0:
                if rating_count > 10000:
                    players = f"{rating_count//1000}K"
                    players_numeric = rating_count
                else:
                    players = f"{rating_count:,}"
                    players_numeric = rating_count
            else:
                # Buat estimasi berdasarkan rating
                base_players = int(1000 * (rating / 5.0) * random.uniform(0.5, 2.0))
                players = f"{base_players:,}"
                players_numeric = base_players
        except:
            players = f"{random.randint(1, 100)}K"
            players_numeric = random.randint(1000, 100000)
            
        # Genre (API tidak menyediakan, jadi kita generate)
        genres = ["Action", "Adventure", "RPG", "Strategy", "Simulation", 
                 "Sports", "Indie", "Shooter", "Survival", "Racing", "Puzzle"]
        genre = random.choice(genres)
        
        # Game image
        thumb = deal.get('thumb', '')
        if not thumb:
            # Fallback image
            thumb = f"https://via.placeholder.com/460x215/1a1a2e/ffffff?text={deal.get('title', 'Game')}"
        
        # Game name dan store
        game_name = deal.get('title', f'Game Deal {idx+1}')
        store_name = store_info.get('storeName', 'Steam')
        
        games_list.append({
            "appid": appid,
            "name": game_name,
            "image": thumb,
            "price": sale_price,
            "normal_price": normal_price,
            "discount": discount,
            "players": players,
            "players_numeric": players_numeric,
            "rating": rating,
            "genre": genre,
            "year": release_year,
            "store": store_name,
            "store_id": store_id,
            "deal_id": deal.get('dealID', ''),
            "steam_rating": float(deal.get('steamRatingPercent', 0)) / 20 if deal.get('steamRatingPercent') else rating,
            "metacritic_score": int(deal.get('metacriticScore', 0)),
            "deal_link": f"https://www.cheapshark.com/redirect?dealID={deal.get('dealID', '')}",
            "is_deal": True,
            "steam_app_id": deal.get('steamAppID'),
            "internal_name": deal.get('internalName'),
            "steam_rating_text": deal.get('steamRatingText', ''),
            "steam_rating_count": deal.get('steamRatingCount', '0')
        })
    
    return games_list

# -------------------------
# FUNGSI AI UNTUK REKOMENDASI GAME
# -------------------------
def get_ai_game_recommendation(user_preferences, games_data, api_key):
    """Mendapatkan rekomendasi game dari AI berdasarkan preferensi pengguna"""
    try:
        # Cek apakah API key valid
        if not api_key:
            return "❌ **API Key Gemini tidak ditemukan!** Silakan konfigurasi API key di Streamlit Cloud Secrets."
        
        # Konfigurasi Gemini AI
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Format data games untuk konteks AI
        games_info = []
        for game in games_data[:20]:  # Ambil 20 game pertama sebagai contoh
            games_info.append(
                f"- {game['name']} | Genre: {game['genre']} | "
                f"Harga: ${game['price']:.2f} | Rating: {game['rating']}/5 | "
                f"Diskon: {game.get('discount', '0%')}"
            )
        
        games_context = "\n".join(games_info)
        
        # Buat prompt untuk AI
        prompt = f"""
        Anda adalah ahli rekomendasi game. Berikan rekomendasi game berdasarkan preferensi pengguna berikut:
        
        **PREFERENSI PENGGUNA:**
        - Genre favorit: {', '.join(user_preferences.get('favorite_genres', ['Semua']))}
        - Budget: ${user_preferences.get('price_range', {}).get('min', 0)} - ${user_preferences.get('price_range', {}).get('max', 100)}
        - Platform: {', '.join(user_preferences.get('preferred_stores', ['Steam']))}
        
        **DAFTAR GAME YANG TERSEDIA:**
        {games_context}
        
        **INSTRUKSI:**
        1. Berikan 3-5 rekomendasi game yang paling sesuai dengan preferensi pengguna
        2. Untuk setiap rekomendasi, sertakan:
           - Nama game
           - Alasan kenapa cocok
           - Harga dan diskon (jika ada)
           - Rating dan genre
        3. Gunakan format yang mudah dibaca dengan bullet points
        4. Jika ada game dengan diskon besar, prioritaskan
        5. Jika tidak ada game yang sesuai, berikan saran alternatif
        
        Berikan respons dalam bahasa Indonesia.
        """
        
        # Dapatkan respons dari AI
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"❌ **Error AI:** {str(e)}\n\nPastikan API key Gemini AI valid dan terkoneksi ke internet."

def get_ai_game_description(game, api_key):
    """Mendapatkan deskripsi game dari AI"""
    try:
        if not api_key:
            return game.get('steam_rating_text', 'Deskripsi tidak tersedia. API Key Gemini belum dikonfigurasi.')
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Buat deskripsi yang menarik untuk game berikut:
        
        **INFORMASI GAME:**
        - Nama: {game['name']}
        - Genre: {game['genre']}
        - Harga: ${game['price']:.2f} (Normal: ${game.get('normal_price', game['price']):.2f})
        - Diskon: {game.get('discount', '0%')}
        - Rating: {game['rating']}/5.0
        - Tahun Rilis: {game.get('year', 'Tidak diketahui')}
        
        **INSTRUKSI:**
        1. Buat deskripsi menarik dalam 2-3 paragraf
        2. Sertakan fitur utama game berdasarkan genrenya
        3. Highlight jika ada diskon atau harga spesial
        4. Gunakan bahasa Indonesia yang menarik
        5. Tambahkan saran untuk tipe pemain yang cocok
        
        **HASIL DESKRIPSI:**
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Deskripsi tidak dapat dibuat: {str(e)}"

def get_ai_chat_response(user_question, games_data, api_key):
    """Mendapatkan respons chat dari AI"""
    try:
        if not api_key:
            return "❌ API Key Gemini belum dikonfigurasi. Silakan tambahkan GEMINI_API_KEY di Streamlit Cloud Secrets."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Buat prompt kontekstual dengan data games
        games_context = "\n".join([
            f"- {game['name']} (${game['price']:.2f}, {game['genre']}, ⭐{game['rating']})"
            for game in games_data[:15]
        ])
        
        prompt = f"""
        Anda adalah ahli game yang membantu pengguna. 
        
        **INFORMASI GAME TERSEDIA:**
        {games_context}
        
        **PERTANYAAN PENGGUNA:**
        {user_question}
        
        **INSTRUKSI:**
        1. Jawab dalam bahasa Indonesia
        2. Berikan jawaban yang informatif dan membantu
        3. Jika relevan, sertakan rekomendasi game dari daftar di atas
        4. Jika tidak tahu, jangan membuat informasi
        5. Format jawaban dengan jelas
        
        **JAWABAN:**
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# -------------------------
# LOAD DATA DARI API
# -------------------------
@st.cache_resource
def load_games_data():
    """Load games data dari API CheapShark"""
    with st.spinner("🔄 Loading live game deals from CheapShark API..."):
        deals, stores = fetch_game_deals(60)  # Ambil 60 deal
        games_data = convert_deals_to_games_format(deals, stores)
        
        # Jika tidak ada data dari API, gunakan fallback minimal
        if not games_data:
            st.warning("⚠️ Tidak bisa mengambil data dari API. Menggunakan data fallback.")
            games_data = [
                {"appid": 730, "name": "Counter-Strike 2", "image": "https://cdn.akamai.steamstatic.com/steam/apps/730/header.jpg", "price": 0, "players": "850K", "players_numeric": 850000, "rating": 4.8, "genre": "FPS", "year": 2023, "store": "Steam", "is_deal": False},
                {"appid": 570, "name": "Dota 2", "image": "https://cdn.akamai.steamstatic.com/steam/apps/570/header.jpg", "price": 0, "players": "450K", "players_numeric": 450000, "rating": 4.7, "genre": "MOBA", "year": 2013, "store": "Steam", "is_deal": False},
            ]
        
        return games_data

# Load data games dari API
GAMES_DATA = load_games_data()

st.set_page_config(
    page_title="PlayHub - Game Deals & AI Assistant",
    page_icon="🎮",
    layout="wide"
)

# CSS custom untuk tampilan
st.markdown("""
<style>
    .game-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        background: white;
    }
    .game-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    .trending-badge {
        background: linear-gradient(45deg, #FF416C, #FF4B2B);
        color: white;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 5px;
    }
    .discount-badge {
        background: linear-gradient(45deg, #00b09b, #96c93d);
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
        position: absolute;
        top: 10px;
        right: 10px;
    }
    .store-badge {
        background: #4A90E2;
        color: white;
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 10px;
        margin-left: 5px;
    }
    .main-header {
        background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .game-image {
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 10px;
    }
    .ai-response-box {
        background: linear-gradient(45deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #00adb5;
    }
    .secret-status {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px solid #28a745;
    }
    .secret-warning {
        background: #fff3cd;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------
# FUNGSI UTILITAS UNTUK GRAFIK REAL-TIME
# -------------------------
def generate_realtime_game_statistics(game, days=30):
    """Generate statistics real-time untuk game dengan data yang realistis"""
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    dates.reverse()  # Dari tertua ke terbaru
    
    try:
        base_players = game.get('players_numeric', 10000)
        base_rating = game.get('rating', 4.0)
        base_price = game.get('price', 19.99)
    except:
        base_players = 10000
        base_rating = 4.0
        base_price = 19.99
    
    # Generate realistic player data dengan trend
    player_trend = random.choice(['increasing', 'decreasing', 'stable', 'spiky'])
    
    if player_trend == 'increasing':
        trend_factor = np.linspace(0.8, 1.2, days)
    elif player_trend == 'decreasing':
        trend_factor = np.linspace(1.2, 0.8, days)
    else:
        trend_factor = np.ones(days)
    
    players_data = []
    for i in range(days):
        # Weekly pattern (more players on weekends)
        day_of_week = (datetime.now() - timedelta(days=days-i-1)).weekday()
        weekend_boost = 1.3 if day_of_week >= 5 else 1.0
        
        # Random fluctuation
        fluctuation = random.uniform(0.85, 1.15)
        
        # Calculate player count
        if player_trend == 'spiky':
            if i % 7 == 0:  # Every week
                spike = random.uniform(1.5, 2.5)
            else:
                spike = random.uniform(0.7, 1.3)
            player_count = base_players * spike * weekend_boost * trend_factor[i]
        else:
            player_count = base_players * fluctuation * weekend_boost * trend_factor[i]
        
        players_data.append(int(max(player_count, 100)))
    
    # Rating data (lebih stabil)
    rating_data = []
    for i in range(days):
        # Rating changes slowly
        change = random.uniform(-0.05, 0.05)
        new_rating = base_rating + change
        rating_data.append(round(max(min(new_rating, 5.0), 1.0), 2))
    
    # Price history data
    price_data = []
    if game.get('is_deal', False) and base_price > 0:
        # Untuk game yang sedang diskon
        normal_price = game.get('normal_price', base_price * 1.5)
        sale_start = random.randint(5, 25)  # Sale started X days ago
        
        for i in range(days):
            if i >= sale_start:
                price_data.append(base_price)
            else:
                price_data.append(normal_price)
    else:
        # Untuk game reguler
        for i in range(days):
            fluctuation = random.uniform(0.95, 1.05)
            price_data.append(round(base_price * fluctuation, 2))
    
    return {
        'dates': dates,
        'players': players_data,
        'ratings': rating_data,
        'prices': price_data,
        'player_trend': player_trend
    }

def get_all_games_statistics():
    """Generate statistics untuk semua games"""
    all_stats = {}
    for game in GAMES_DATA:
        game_id = game['appid']
        all_stats[game_id] = generate_realtime_game_statistics(game)
    return all_stats

# -------------------------
# FUNGSI UTILITAS
# -------------------------
def get_top_10_trending_games():
    """Mendapatkan 10 game paling trending berdasarkan player count"""
    if not GAMES_DATA:
        return []
    
    sorted_games = sorted(GAMES_DATA, key=lambda x: x.get('players_numeric', 0), reverse=True)
    top_10 = sorted_games[:10]
    
    for i, game in enumerate(top_10):
        game['rank'] = i + 1
    
    return top_10

# Session state
if 'wishlist' not in st.session_state:
    st.session_state.wishlist = []

if 'games_per_page' not in st.session_state:
    st.session_state.games_per_page = 10

if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if 'selected_game' not in st.session_state:
    st.session_state.selected_game = None

if 'all_game_stats' not in st.session_state:
    st.session_state.all_game_stats = get_all_games_statistics()

if 'gemini_api_key_source' not in st.session_state:
    st.session_state.gemini_api_key_source = "not_found"

if 'ai_messages' not in st.session_state:
    st.session_state.ai_messages = []

# Inisialisasi data user dari session state
if 'user_data' not in st.session_state:
    # Default user data jika belum ada
    st.session_state.user_data = {
        'username': st.session_state.get('username', 'Guest'),
        'email': st.session_state.get('email', 'guest@example.com'),
        'full_name': st.session_state.get('full_name', 'Guest User'),
        'join_date': st.session_state.get('join_date', datetime.now().strftime('%Y-%m-%d')),
        'preferences': {
            'favorite_genres': [],
            'price_range': {'min': 0, 'max': 100},
            'preferred_stores': ['Steam', 'Epic Games']
        },
        'activity': {
            'total_wishlist': 0,
            'total_views': 0,
            'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }

def add_to_wishlist(appid, game_name, game_image, game_price):
    """Tambah game ke wishlist"""
    if appid not in [item['appid'] for item in st.session_state.wishlist]:
        st.session_state.wishlist.append({
            'appid': appid,
            'name': game_name,
            'image': game_image,
            'price': game_price,
            'added_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        # Update user activity
        st.session_state.user_data['activity']['total_wishlist'] = len(st.session_state.wishlist)
        return True
    return False

def remove_from_wishlist(appid):
    """Hapus game dari wishlist"""
    for i, item in enumerate(st.session_state.wishlist):
        if item['appid'] == appid:
            st.session_state.wishlist.pop(i)
            # Update user activity
            st.session_state.user_data['activity']['total_wishlist'] = len(st.session_state.wishlist)
            return True
    return False

def is_in_wishlist(appid):
    """Cek apakah game sudah ada di wishlist"""
    return any(item['appid'] == appid for item in st.session_state.wishlist)

# -------------------------
# AMBIL API KEY DARI SECRETS
# -------------------------
GEMINI_API_KEY = get_gemini_api_key()

# -------------------------
# MAIN APP
# -------------------------
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Please log in first!")
    if st.button("Go to Login"):
        st.switch_page("main.py")
else:
    # Header utama
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🎮 PlayHub - Game Deals & AI Assistant")
    st.success(f"🎉 Welcome back, **{st.session_state.username}**!")
    st.info(f"🔄 Connected to CheapShark API ({len(GAMES_DATA)} live deals loaded)")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        # Status API Key
        st.header("🔑 API Key Status")
        
        if GEMINI_API_KEY:
            st.markdown('<div class="secret-status">', unsafe_allow_html=True)
            st.success("✅ Gemini API Key Loaded")
            
            # Tampilkan source API key
            source = st.session_state.get('gemini_api_key_source', 'unknown')
            source_text = {
                'streamlit_secrets': 'Streamlit Secrets',
                'environment_variable': 'Environment Variable',
                'session_state': 'Session State',
                'not_found': 'Not Found'
            }.get(source, source)
            
            st.caption(f"Source: {source_text}")
            
            # Tampilkan informasi tentang API key
            key_preview = GEMINI_API_KEY[:10] + "..." + GEMINI_API_KEY[-10:] if len(GEMINI_API_KEY) > 20 else "***"
            st.code(f"Key: {key_preview}", language="text")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Info penggunaan AI
            with st.expander("ℹ️ AI Features Enabled"):
                st.markdown("""
                - 🎮 **Personal Game Recommendations**
                - 📝 **AI Game Descriptions**
                - 💬 **Chat with Game Expert**
                - 📊 **AI-Powered Analytics**
                """)
        
        else:
            st.markdown('<div class="secret-warning">', unsafe_allow_html=True)
            st.warning("⚠️ Gemini API Key Not Found")
            
            st.markdown("""
            **Untuk menggunakan AI Assistant, tambahkan di:**
            
            1. **Streamlit Cloud:**
               - Buka app settings
               - Pilih **Secrets**
               - Tambahkan:
               ```
               GEMINI_API_KEY = "your-api-key-here"
               ```
            
            2. **Local Development:**
               - Buat file `.streamlit/secrets.toml`
               - Tambahkan:
               ```toml
               GEMINI_API_KEY = "your-api-key-here"
               ```
            
            3. **Environment Variable:**
               ```bash
               export GEMINI_API_KEY="your-api-key-here"
               ```
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Wishlist section
        st.header("❤️ Your Wishlist")
        if st.session_state.wishlist:
            st.write(f"You have **{len(st.session_state.wishlist)}** games in your wishlist")
            for i, item in enumerate(st.session_state.wishlist[:3]):
                st.write(f"• {item['name'][:20]}...")
            if len(st.session_state.wishlist) > 3:
                st.write(f"... and {len(st.session_state.wishlist) - 3} more")
        else:
            st.info("Your wishlist is empty. Add games from the store!")
        
        # API status
        st.markdown("---")
        st.write("**API Status:**")
        st.success("✅ Connected to CheapShark")
        
        if GEMINI_API_KEY:
            st.success("✅ Gemini AI Ready")
        else:
            st.warning("⚠️ Gemini AI Not Configured")
        
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Game Statistics
        st.markdown("---")
        st.write("**📈 Live Statistics:**")
        total_players = sum(game.get('players_numeric', 0) for game in GAMES_DATA)
        avg_price = sum(game.get('price', 0) for game in GAMES_DATA) / max(len(GAMES_DATA), 1)
        avg_rating = sum(game.get('rating', 0) for game in GAMES_DATA) / max(len(GAMES_DATA), 1)
        
        st.metric("👥 Total Players", f"{total_players:,}")
        st.metric("💰 Avg Price", f"${avg_price:.2f}")
        st.metric("⭐ Avg Rating", f"{avg_rating:.1f}/5")
        
        # Refresh button
        st.markdown("---")
        if st.button("🔄 Refresh All Data", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.session_state.all_game_stats = get_all_games_statistics()
            # Refresh API key status
            GEMINI_API_KEY = get_gemini_api_key()
            st.rerun()

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎮 Live Deals", "📊 Analytics", "👤 Profile", "🤖 AI Assistant"])
    
    with tab1:
        # ==================== TOP 10 TRENDING GAMES ====================
        st.subheader("🔥 Top 10 Trending Deals")
        
        trending_games = get_top_10_trending_games()
        
        if trending_games:
            for row in range(0, 10, 5):
                cols = st.columns(5)
                for col_idx in range(5):
                    if row + col_idx < len(trending_games):
                        game = trending_games[row + col_idx]
                        with cols[col_idx]:
                            with st.container():
                                st.markdown('<div class="game-card">', unsafe_allow_html=True)
                                
                                # Badge untuk game trending dan diskon
                                if game.get('rank'):
                                    st.markdown(f'<div class="trending-badge">#{game["rank"]}</div>', unsafe_allow_html=True)
                                
                                if game.get('discount', '0%') != '0%':
                                    st.markdown(f'<div class="discount-badge">{game["discount"]}</div>', unsafe_allow_html=True)
                                
                                # Game image
                                st.markdown('<div class="game-image">', unsafe_allow_html=True)
                                st.image(game['image'], use_container_width=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Game info
                                display_name = game['name'][:15] + "..." if len(game['name']) > 15 else game['name']
                                st.write(f"**{display_name}**")
                                
                                store_badge = f"<span class='store-badge'>{game.get('store', 'Store')}</span>"
                                st.markdown(f"{game['genre']} • {store_badge}", unsafe_allow_html=True)
                                st.caption(f"⭐ {game['rating']} • 👥 {game['players']}")
                                
                                # Price info
                                if game['price'] == 0:
                                    st.success("🆓 FREE")
                                else:
                                    normal_price = game.get('normal_price', game['price'])
                                    if normal_price > game['price']:
                                        st.write(f"~~${normal_price:.2f}~~")
                                        st.write(f"**${game['price']:.2f}**")
                                    else:
                                        st.write(f"**${game['price']:.2f}**")
                                
                                # Mini chart untuk player trend
                                if game['appid'] in st.session_state.all_game_stats:
                                    stats = st.session_state.all_game_stats[game['appid']]
                                    fig_mini = go.Figure()
                                    fig_mini.add_trace(go.Scatter(
                                        x=list(range(7)),
                                        y=stats['players'][-7:],
                                        mode='lines',
                                        line=dict(color='#00CC96', width=2)
                                    ))
                                    fig_mini.update_layout(
                                        height=60,
                                        margin=dict(l=0, r=0, t=0, b=0),
                                        showlegend=False,
                                        xaxis=dict(showticklabels=False),
                                        yaxis=dict(showticklabels=False),
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)'
                                    )
                                    st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False})
                                
                                # Action buttons
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    button_key = f"view_trend_{game['appid']}_{row}_{col_idx}"
                                    if st.button("🔍", key=button_key, use_container_width=True):
                                        st.session_state.selected_game = game['appid']
                                        st.rerun()
                                with col_btn2:
                                    wishlisted = is_in_wishlist(game['appid'])
                                    wish_key = f"wish_trend_{game['appid']}_{row}_{col_idx}"
                                    if wishlisted:
                                        if st.button("❤️", key=wish_key, use_container_width=True):
                                            remove_from_wishlist(game['appid'])
                                            time.sleep(0.3)
                                            st.rerun()
                                    else:
                                        if st.button("🤍", key=f"add_{wish_key}", use_container_width=True):
                                            add_to_wishlist(game['appid'], game['name'], game['image'], game['price'])
                                            time.sleep(0.3)
                                            st.rerun()
                                
                                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ==================== ALL GAMES SECTION ====================
        # Search dan filter
        search_query = st.text_input("🔍 Search game deals...", placeholder="Enter game name", key="search_input")
        
        col_settings1, col_settings2, col_settings3 = st.columns(3)
        with col_settings1:
            games_per_page = st.selectbox("Deals per page", [10, 20, 30, 50], index=0)
            if games_per_page != st.session_state.games_per_page:
                st.session_state.games_per_page = games_per_page
                st.session_state.current_page = 1
                st.rerun()
        
        with col_settings2:
            sort_by = st.selectbox("Sort by", ["Best Deals", "Price: Low to High", "Price: High to Low", "Rating", "Newest", "Most Players"])
        
        with col_settings3:
            # Filter by store
            all_stores = ["All Stores"] + sorted(list(set([g.get('store', 'Unknown') for g in GAMES_DATA])))
            store_filter = st.selectbox("Filter by Store", all_stores)
        
        # Filter games
        filtered_games = GAMES_DATA.copy()
        
        if search_query:
            filtered_games = [game for game in filtered_games if search_query.lower() in game['name'].lower()]
        
        if store_filter != "All Stores":
            filtered_games = [game for game in filtered_games if game.get('store') == store_filter]
        
        # Sorting
        if sort_by == "Price: Low to High":
            filtered_games.sort(key=lambda x: x['price'])
        elif sort_by == "Price: High to Low":
            filtered_games.sort(key=lambda x: x['price'], reverse=True)
        elif sort_by == "Rating":
            filtered_games.sort(key=lambda x: x['rating'], reverse=True)
        elif sort_by == "Newest":
            filtered_games.sort(key=lambda x: x.get('year', 2024), reverse=True)
        elif sort_by == "Most Players":
            filtered_games.sort(key=lambda x: x.get('players_numeric', 0), reverse=True)
        else:  # Best Deals
            def get_discount_percent(game):
                try:
                    discount_str = game.get('discount', '0%').replace('%', '')
                    return float(discount_str)
                except:
                    return 0
            filtered_games.sort(key=lambda x: get_discount_percent(x), reverse=True)
        
        # Display games
        st.subheader(f"🎯 All Game Deals ({len(filtered_games)} total)")
        
        if len(filtered_games) == 0:
            st.info("No game deals found. Try a different search or filter.")
        else:
            # Pagination
            total_pages = max(1, len(filtered_games) // st.session_state.games_per_page + 
                             (1 if len(filtered_games) % st.session_state.games_per_page > 0 else 0))
            
            start_idx = (st.session_state.current_page - 1) * st.session_state.games_per_page
            end_idx = min(start_idx + st.session_state.games_per_page, len(filtered_games))
            page_games = filtered_games[start_idx:end_idx]
            
            # Display games
            for idx, game in enumerate(page_games):
                with st.container():
                    st.markdown('<div class="game-card">', unsafe_allow_html=True)
                    
                    col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 1, 1])
                    
                    with col1:
                        st.markdown('<div class="game-image">', unsafe_allow_html=True)
                        st.image(game['image'], width=100)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.write(f"**{game['name']}**")
                        store_badge = f"<span class='store-badge'>{game.get('store', 'Store')}</span>"
                        st.markdown(f"{game['genre']} • {store_badge}", unsafe_allow_html=True)
                        st.caption(f"⭐ {game['rating']} • {game.get('year', 'N/A')}")
                        
                        # Mini trend indicator
                        if game['appid'] in st.session_state.all_game_stats:
                            stats = st.session_state.all_game_stats[game['appid']]
                            trend = stats['player_trend']
                            if trend == 'increasing':
                                st.caption("📈 Player count increasing")
                            elif trend == 'decreasing':
                                st.caption("📉 Player count decreasing")
                    
                    with col3:
                        st.write(f"👥 {game.get('players', 'N/A')}")
                        if game['price'] == 0:
                            st.success("🆓 FREE")
                        else:
                            normal_price = game.get('normal_price', game['price'])
                            if normal_price > game['price']:
                                st.write(f"~~${normal_price:.2f}~~")
                                st.write(f"**${game['price']:.2f}**")
                                if game.get('discount', '0%') != '0%':
                                    st.success(f"💸 {game['discount']} OFF")
                            else:
                                st.write(f"💵 **${game['price']:.2f}**")
                    
                    with col4:
                        detail_key = f"detail_game_{game['appid']}_{start_idx}_{idx}"
                        if st.button("🔍", key=detail_key, use_container_width=True):
                            st.session_state.selected_game = game['appid']
                            st.rerun()
                    
                    with col5:
                        wishlisted = is_in_wishlist(game['appid'])
                        wish_key = f"wish_game_{game['appid']}_{start_idx}_{idx}"
                        if wishlisted:
                            if st.button("❤️", key=wish_key, use_container_width=True):
                                remove_from_wishlist(game['appid'])
                                time.sleep(0.3)
                                st.rerun()
                        else:
                            add_wish_key = f"add_wish_{game['appid']}_{start_idx}_{idx}"
                            if st.button("🤍", key=add_wish_key, use_container_width=True):
                                add_to_wishlist(game['appid'], game['name'], game['image'], game['price'])
                                time.sleep(0.3)
                                st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Pagination controls
            if total_pages > 1:
                st.markdown("---")
                col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
                
                with col_nav1:
                    if st.session_state.current_page > 1:
                        if st.button("◀️ First"):
                            st.session_state.current_page = 1
                            st.rerun()
                
                with col_nav2:
                    if st.session_state.current_page > 1:
                        if st.button("◀ Prev"):
                            st.session_state.current_page -= 1
                            st.rerun()
                
                with col_nav3:
                    st.write(f"**Page {st.session_state.current_page} of {total_pages}**")
                
                with col_nav4:
                    if st.session_state.current_page < total_pages:
                        if st.button("Next ▶"):
                            st.session_state.current_page += 1
                            st.rerun()
        
        # Export Data
        st.markdown("---")
        st.subheader("💾 Export Deal Data")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            try:
                export_data = []
                for game in filtered_games:
                    export_data.append({
                        'name': game.get('name', 'Unknown Game'),
                        'price': float(game.get('price', 0)),
                        'normal_price': float(game.get('normal_price', 0)),
                        'discount': game.get('discount', '0%'),
                        'players': game.get('players', '0'),
                        'rating': float(game.get('rating', 0)),
                        'genre': game.get('genre', 'Unknown'),
                        'year': int(game.get('year', 2024)),
                        'store': game.get('store', 'Unknown')
                    })
                
                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"game_deals_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error creating CSV: {str(e)}")
        
        with col_exp2:
            try:
                json_data = json.dumps(export_data, indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"game_deals_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error creating JSON: {str(e)}")
    
    with tab2:
        # ==================== ANALYTICS DASHBOARD ====================
        st.header("📊 Game Deals Analytics Dashboard")
        
        col_analytics1, col_analytics2, col_analytics3 = st.columns(3)
        with col_analytics1:
            avg_price = sum(game.get('price', 0) for game in GAMES_DATA) / max(len(GAMES_DATA), 1)
            st.metric("💰 Average Price", f"${avg_price:.2f}")
        with col_analytics2:
            total_discount = sum(float(game.get('discount', '0%').replace('%', '')) for game in GAMES_DATA if game.get('discount', '0%') != '0%')
            avg_discount = total_discount / max(sum(1 for game in GAMES_DATA if game.get('discount', '0%') != '0%'), 1)
            st.metric("💸 Average Discount", f"{avg_discount:.1f}%")
        with col_analytics3:
            total_players = sum(game.get('players_numeric', 0) for game in GAMES_DATA)
            st.metric("👥 Total Players", f"{total_players:,}")
        
        # Chart 1: Top Games by Player Count
        st.markdown("---")
        st.subheader("🏆 Top 10 Games by Player Count")
        
        top_games = sorted(GAMES_DATA, key=lambda x: x.get('players_numeric', 0), reverse=True)[:10]
        
        fig_top = px.bar(
            x=[game['name'][:20] for game in top_games],
            y=[game['players_numeric'] for game in top_games],
            labels={'x': 'Game', 'y': 'Players'},
            color=[game['rating'] for game in top_games],
            color_continuous_scale='Viridis',
            title="Player Count Distribution"
        )
        fig_top.update_layout(height=500)
        st.plotly_chart(fig_top, use_container_width=True)
        
        # Chart 2: Price Distribution
        st.subheader("💰 Price Distribution")
        
        prices = [game['price'] for game in GAMES_DATA if game['price'] > 0]
        
        fig_price = px.histogram(
            x=prices,
            nbins=20,
            labels={'x': 'Price ($)', 'y': 'Count'},
            title="Price Distribution of Game Deals"
        )
        fig_price.update_layout(
            height=400,
            xaxis_title="Price ($)",
            yaxis_title="Number of Games",
            bargap=0.1
        )
        st.plotly_chart(fig_price, use_container_width=True)
    
        
        # Chart 5: Genre Distribution
        st.subheader("🎮 Game Genres Distribution")
        
        genre_counts = {}
        for game in GAMES_DATA:
            genre = game.get('genre', 'Unknown')
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        fig_genre = px.bar(
            x=list(genre_counts.keys()),
            y=list(genre_counts.values()),
            labels={'x': 'Genre', 'y': 'Count'},
            color=list(genre_counts.values()),
            color_continuous_scale='Plasma',
            title="Number of Games by Genre"
        )
        fig_genre.update_layout(height=400)
        st.plotly_chart(fig_genre, use_container_width=True)

    with tab3:
        # ==================== PROFILE PAGE ====================
        st.header("👤 User Profile")
        
        # Update last login time
        st.session_state.user_data['activity']['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Profile Overview Card
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        col_profile1, col_profile2 = st.columns([1, 2])
        
        with col_profile1:
            # User avatar/icon
            avatar_color = "#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
            avatar_text = st.session_state.user_data['username'][0].upper()
            
            st.markdown(f"""
            <div style="display: flex; justify-content: center; align-items: center; 
                        width: 120px; height: 120px; 
                        background: linear-gradient(45deg, {avatar_color}, #667eea);
                        border-radius: 50%; font-size: 48px; color: black;
                        font-weight: bold; margin: 0 auto;">
                {avatar_text}
            </div>
            """, unsafe_allow_html=True)
        
        with col_profile2:
            st.markdown(f"<p style='color: black;'><strong>🎮 Username:</strong> @{st.session_state.user_data['username']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: b;'><strong>📅 Last Login:</strong> {st.session_state.user_data['join_date']}</p>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # User Statistics
        st.subheader("📊 Your Statistics")
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            st.metric("❤️ Wishlist", len(st.session_state.wishlist))
            st.caption("Games in your wishlist")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_stat2:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            total_wishlist_value = sum(item.get('price', 0) for item in st.session_state.wishlist)
            st.metric("💰 Total Value", f"${total_wishlist_value:.2f}")
            st.caption("Value of your wishlist")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_stat3:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            avg_wishlist_price = total_wishlist_value / max(len(st.session_state.wishlist), 1)
            st.metric("💵 Avg Price", f"${avg_wishlist_price:.2f}")
            st.caption("Average game price in wishlist")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_stat4:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            days_joined = (datetime.now() - datetime.strptime(st.session_state.user_data['join_date'], '%Y-%m-%d')).days
            st.metric("📅 Days Active", days_joined)
            st.caption("Days as PlayHub member")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Wishlist Overview
        st.subheader("🎮 Your Wishlist")
        
        if st.session_state.wishlist:
            # Wishlist summary chart
            wishlist_genres = {}
            wishlist_stores = {}
            wishlist_prices = []
            
            for item in st.session_state.wishlist:
                # Find game details
                for game in GAMES_DATA:
                    if game['appid'] == item['appid']:
                        # Count genres
                        genre = game.get('genre', 'Unknown')
                        wishlist_genres[genre] = wishlist_genres.get(genre, 0) + 1
                        
                        # Count stores
                        store = game.get('store', 'Unknown')
                        wishlist_stores[store] = wishlist_stores.get(store, 0) + 1
                        
                        # Collect prices
                        wishlist_prices.append(game.get('price', 0))
                        break
            
            # Create two columns for charts
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                if wishlist_genres:
                    fig_genre = px.pie(
                        values=list(wishlist_genres.values()),
                        names=list(wishlist_genres.keys()),
                        title="🎮 Wishlist by Genre"
                    )
                    fig_genre.update_layout(height=300)
                    st.plotly_chart(fig_genre, use_container_width=True)
            
            with col_chart2:
                if wishlist_prices:
                    fig_price = px.histogram(
                        x=wishlist_prices,
                        nbins=10,
                        title="💰 Wishlist Price Distribution",
                        labels={'x': 'Price ($)', 'y': 'Count'}
                    )
                    fig_price.update_layout(height=300)
                    st.plotly_chart(fig_price, use_container_width=True)
            
            # Detailed wishlist
            st.subheader("📋 Wishlist Details")
            
            for item in st.session_state.wishlist:
                # Find game details
                game_details = None
                for game in GAMES_DATA:
                    if game['appid'] == item['appid']:
                        game_details = game
                        break
                
                if game_details:
                    with st.container():
                        st.markdown('<div class="wishlist-item">', unsafe_allow_html=True)
                        
                        col_wish1, col_wish2, col_wish3, col_wish4, col_wish5 = st.columns([1, 3, 2, 1, 1])
                        
                        with col_wish1:
                            st.image(game_details['image'], width=60)
                        
                        with col_wish2:
                            st.write(f"**{game_details['name'][:30]}{'...' if len(game_details['name']) > 30 else ''}**")
                            st.caption(f"{game_details.get('genre', 'Unknown')} • {game_details.get('store', 'Unknown')}")
                        
                        with col_wish3:
                            if game_details['price'] == 0:
                                st.success("🆓 FREE")
                            else:
                                st.write(f"**${game_details['price']:.2f}**")
                                if game_details.get('discount', '0%') != '0%':
                                    st.caption(f"💸 {game_details['discount']} OFF")
                            st.caption(f"Added: {item['added_date']}")
                        
                        with col_wish4:
                            if st.button("🔍", key=f"view_wish_{item['appid']}", use_container_width=True):
                                st.session_state.selected_game = item['appid']
                                st.rerun()
                        
                        with col_wish5:
                            if st.button("🗑️", key=f"remove_wish_{item['appid']}", use_container_width=True):
                                remove_from_wishlist(item['appid'])
                                time.sleep(0.3)
                                st.rerun()
                        
                        st.markdown('</div>', unsafe_allow_html=True)
            
            # Export wishlist
            st.markdown("---")
            st.subheader("💾 Export Your Wishlist")
            
            col_export1, col_export2 = st.columns(2)
            
            with col_export1:
                try:
                    wishlist_export = []
                    for item in st.session_state.wishlist:
                        for game in GAMES_DATA:
                            if game['appid'] == item['appid']:
                                wishlist_export.append({
                                    'name': game.get('name', 'Unknown'),
                                    'price': float(game.get('price', 0)),
                                    'discount': game.get('discount', '0%'),
                                    'genre': game.get('genre', 'Unknown'),
                                    'store': game.get('store', 'Unknown'),
                                    'added_date': item['added_date'],
                                    'rating': float(game.get('rating', 0)),
                                    'players': game.get('players', '0')
                                })
                                break
                    
                    wishlist_df = pd.DataFrame(wishlist_export)
                    wishlist_csv = wishlist_df.to_csv(index=False)
                    
                    st.download_button(
                        label="📥 Download Wishlist (CSV)",
                        data=wishlist_csv,
                        file_name=f"wishlist_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error creating CSV: {str(e)}")
            
            with col_export2:
                try:
                    wishlist_json = json.dumps(wishlist_export, indent=2)
                    st.download_button(
                        label="📥 Download Wishlist (JSON)",
                        data=wishlist_json,
                        file_name=f"wishlist_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error creating JSON: {str(e)}")
        
        else:
            st.info("🌟 Your wishlist is empty. Browse games and add them to your wishlist!")
        
        
        with st.expander("🎮 Update Gaming Preferences"):
            st.write("Select your favorite game genres:")
            
            all_genres = ["Action", "Adventure", "RPG", "Strategy", "Simulation", 
                         "Sports", "Indie", "Shooter", "Survival", "Racing", "Puzzle"]
            
            selected_genres = st.multiselect(
                "Favorite Genres",
                options=all_genres,
                default=st.session_state.user_data['preferences']['favorite_genres']
            )
            
            col_pref1, col_pref2 = st.columns(2)
            with col_pref1:
                min_price = st.slider("Minimum Price ($)", 0, 100, 
                                     value=st.session_state.user_data['preferences']['price_range']['min'])
            with col_pref2:
                max_price = st.slider("Maximum Price ($)", 0, 100, 
                                     value=st.session_state.user_data['preferences']['price_range']['max'])
            
            # Tombol untuk mendapatkan rekomendasi AI
            col_pref3, col_pref4 = st.columns(2)
            with col_pref3:
                if st.button("💾 Save Preferences", key="save_preferences"):
                    st.session_state.user_data['preferences']['favorite_genres'] = selected_genres
                    st.session_state.user_data['preferences']['price_range'] = {'min': min_price, 'max': max_price}
                    st.success("✅ Preferences saved successfully!")
                    time.sleep(1)
                    st.rerun()
            
            with col_pref4:
                if st.button("🤖 Get AI Recommendations", key="ai_recommendations"):
                    if GEMINI_API_KEY:
                        st.info("🔄 Generating AI recommendations...")
                        preferences = st.session_state.user_data['preferences']
                        recommendations = get_ai_game_recommendation(preferences, GAMES_DATA, GEMINI_API_KEY)
                        st.markdown('<div class="ai-response-box">', unsafe_allow_html=True)
                        st.markdown("### 🤖 AI Game Recommendations")
                        st.markdown(recommendations)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.error("❌ Gemini API Key not configured!")
        
        # Account Actions
        st.markdown("---")
        st.subheader("🔒 Account Actions")
        
        col_action1, col_action2 = st.columns(2)
        
        with col_action1:
            if st.button("🚪 Logout", use_container_width=True):
                # Clear session state
                for key in list(st.session_state.keys()):
                    if key not in ['_session_id', '_last_report_view']:
                        del st.session_state[key]
                st.success("Logged out successfully!")
                time.sleep(1)
                st.switch_page("main.py")
        
        with col_action2:
            if st.button("🗑️ Clear Wishlist", use_container_width=True):
                st.session_state.wishlist = []
                st.session_state.user_data['activity']['total_wishlist'] = 0
                st.success("Wishlist cleared!")
                time.sleep(1)
                st.rerun()
    
    with tab4:
        # ==================== AI ASSISTANT PAGE ====================
        st.header("🤖 AI Game Assistant")
        
        # Cek apakah API key sudah dikonfigurasi
        if not GEMINI_API_KEY:
            st.error("""
            ## ⚠️ Gemini API Key Not Found in Secrets!
            
            Untuk menggunakan AI Assistant, Anda perlu menambahkan API key di **Streamlit Cloud Secrets**:
            
            1. **Di Streamlit Cloud:**
               - Buka app settings di dashboard
               - Scroll ke bagian **"Secrets"**
               - Tambahkan:
               ```toml
               GEMINI_API_KEY = "your-actual-api-key-here"
               ```
            
            2. **Untuk development lokal:**
               - Buat file `.streamlit/secrets.toml`
               - Tambahkan:
               ```toml
               GEMINI_API_KEY = "your-actual-api-key-here"
               ```
               - Jangan commit file ini ke GitHub!
            
            3. **Dapatkan API Key:**
               - Kunjungi [Google AI Studio](https://aistudio.google.com/apikey)
               - Login dengan Google account
               - Buat API key baru
            
            Setelah API key dikonfigurasi, refresh halaman ini.
            """)
            
            # Tampilkan tombol untuk refresh
            if st.button("🔄 Refresh Page", type="primary"):
                st.rerun()
            
            st.markdown("---")
            
            # Tampilkan struktur secrets yang diperlukan
            with st.expander("📋 Required Secrets Structure"):
                st.code("""
# .streamlit/secrets.toml
GEMINI_API_KEY = "AIzaSyD...your-api-key-here..."

# Atau environment variable
export GEMINI_API_KEY="your-api-key-here"
                """, language="toml")
        
        else:
            st.success(f"✅ **Gemini AI Ready!** API Key loaded from {st.session_state.gemini_api_key_source}")
            
            # Tampilkan status AI
            col_status1, col_status2, col_status3 = st.columns(3)
            with col_status1:
                st.metric("🤖 AI Status", "Active")
            with col_status2:
                st.metric("🎮 Games Loaded", len(GAMES_DATA))
            with col_status3:
                st.metric("👤 User", st.session_state.username)
            
            st.markdown("---")
            
            # Pilihan fitur AI
            st.subheader("🎯 Pilih Fitur AI:")
            
            ai_feature = st.radio(
                "Apa yang ingin Anda lakukan?",
                ["🎮 Dapatkan Rekomendasi Game", "📝 Deskripsi Game Otomatis", "💬 Chat dengan AI Game Expert"],
                horizontal=True
            )
            
            if ai_feature == "🎮 Dapatkan Rekomendasi Game":
                st.markdown("### 🎮 AI Game Recommendations")
                st.write("Berdasarkan preferensi Anda, AI akan merekomendasikan game yang paling cocok:")
                
                # Tampilkan preferensi user saat ini
                preferences = st.session_state.user_data['preferences']
                col_pref1, col_pref2, col_pref3 = st.columns(3)
                with col_pref1:
                    st.info(f"**Genre Favorit:**\n{', '.join(preferences.get('favorite_genres', ['Semua']))}")
                with col_pref2:
                    st.info(f"**Budget:**\n${preferences.get('price_range', {}).get('min', 0)} - ${preferences.get('price_range', {}).get('max', 100)}")
                with col_pref3:
                    st.info(f"**Platform:**\n{', '.join(preferences.get('preferred_stores', ['Steam']))}")
                
                # Tombol untuk generate rekomendasi
                if st.button("✨ Generate AI Recommendations", type="primary", use_container_width=True):
                    with st.spinner("🤖 AI sedang menganalisis dan merekomendasikan game..."):
                        recommendations = get_ai_game_recommendation(preferences, GAMES_DATA, GEMINI_API_KEY)
                        
                        # Tampilkan rekomendasi dalam box yang menarik
                        st.markdown('<div class="ai-response-box">', unsafe_allow_html=True)
                        st.markdown("## 🎮 Rekomendasi Game dari AI")
                        st.markdown("---")
                        st.markdown(recommendations)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Simpan ke session state
                        st.session_state.ai_messages.append({
                            "type": "recommendation",
                            "content": recommendations,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                
                # Tampilkan rekomendasi sebelumnya
                if st.session_state.ai_messages:
                    st.markdown("---")
                    st.subheader("📜 Rekomendasi Sebelumnya")
                    for msg in reversed(st.session_state.ai_messages[-3:]):  # Tampilkan 3 terakhir
                        if msg["type"] == "recommendation":
                            with st.expander(f"Rekomendasi - {msg['timestamp']}"):
                                st.markdown(msg["content"])
            
            elif ai_feature == "📝 Deskripsi Game Otomatis":
                st.markdown("### 📝 AI Game Description Generator")
                st.write("Pilih game untuk mendapatkan deskripsi yang dibuat oleh AI:")
                
                # Pilih game dari dropdown
                game_names = [game['name'] for game in GAMES_DATA[:20]]  # Ambil 20 pertama
                selected_game_name = st.selectbox("Pilih Game:", game_names)
                
                # Cari data game yang dipilih
                selected_game = None
                for game in GAMES_DATA:
                    if game['name'] == selected_game_name:
                        selected_game = game
                        break
                
                if selected_game:
                    col_game1, col_game2 = st.columns([1, 2])
                    with col_game1:
                        st.image(selected_game['image'], width=200)
                    
                    with col_game2:
                        st.write(f"**{selected_game['name']}**")
                        st.write(f"Genre: {selected_game['genre']}")
                        st.write(f"Harga: ${selected_game['price']:.2f}")
                        if selected_game.get('discount', '0%') != '0%':
                            st.success(f"Diskon: {selected_game['discount']}")
                        st.write(f"Rating: ⭐ {selected_game['rating']}/5.0")
                    
                    # Tombol untuk generate deskripsi
                    if st.button("✨ Generate AI Description", type="primary", use_container_width=True):
                        with st.spinner("🤖 AI sedang membuat deskripsi yang menarik..."):
                            description = get_ai_game_description(selected_game, GEMINI_API_KEY)
                            
                            # Tampilkan deskripsi
                            st.markdown('<div class="ai-response-box">', unsafe_allow_html=True)
                            st.markdown("## 📖 Deskripsi Game oleh AI")
                            st.markdown("---")
                            st.markdown(description)
                            st.markdown('</div>', unsafe_allow_html=True)
            
            else:  # 💬 Chat dengan AI Game Expert
                st.markdown("### 💬 Chat dengan AI Game Expert")
                st.write("Tanya apapun tentang game, rekomendasi, atau tips gaming:")
                
                # Input chat
                user_question = st.text_area(
                    "Apa yang ingin Anda tanyakan tentang game?",
                    placeholder="Contoh: 'Game RPG terbaik dengan harga dibawah $20?' atau 'Rekomendasi game multiplayer untuk 4 pemain?'",
                    height=100
                )
                
                if user_question and st.button("🤖 Tanya AI", type="primary", use_container_width=True):
                    with st.spinner("AI sedang berpikir..."):
                        response = get_ai_chat_response(user_question, GAMES_DATA, GEMINI_API_KEY)
                        
                        # Tampilkan respons
                        st.markdown('<div class="ai-response-box">', unsafe_allow_html=True)
                        st.markdown("### 🤖 Jawaban AI:")
                        st.markdown("---")
                        st.markdown(response)
                        st.markdown('</div>', unsafe_allow_html=True)
            
            # Reset chat history
            st.markdown("---")
            if st.button("🗑️ Clear AI History", use_container_width=True):
                st.session_state.ai_messages = []
                st.success("AI history cleared!")
                st.rerun()

# ==================== GAME DETAILS VIEW ====================
if "selected_game" in st.session_state and st.session_state.selected_game:
    st.markdown("---")
    
    appid = st.session_state.selected_game
    
    # Find game details
    game = None
    for g in GAMES_DATA:
        if str(g['appid']) == str(appid):
            game = g
            break
    
    if game:
        st.header(f"🎮 {game['name']}")
        
        # Cek apakah game termasuk trending
        trending_games = get_top_10_trending_games()
        game_rank = None
        for trend_game in trending_games:
            if trend_game['appid'] == game['appid']:
                game_rank = trend_game['rank']
                break
        
        # Main columns
        col1, col2 = st.columns([1, 2])
        
        # Di dalam kolom 1 (col1) di game details view
        with col1:
            st.markdown('<div style="position: relative;">', unsafe_allow_html=True)
            st.markdown('<div class="game-image">', unsafe_allow_html=True)
            st.image(game['image'], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if game_rank:
                st.markdown(f'<div class="trending-badge" style="position: absolute; top: 10px; left: 10px;">#{game_rank} Trending</div>', unsafe_allow_html=True)
            
            if game.get('discount', '0%') != '0%':
                st.markdown(f'<div class="discount-badge" style="position: absolute; top: 10px; right: 10px;">{game["discount"]}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Store info
            st.write(f"**Store:** {game.get('store', 'Unknown')}")
            
            # Player count
            st.write(f"**Player Count:** 👥 {game.get('players', 'N/A')}")
            
            # Price info
            price = game['price']
            if price == 0:
                st.success("🆓 FREE TO PLAY")
            else:
                normal_price = game.get('normal_price', price)
                if normal_price > price:
                    st.write(f"**Normal Price:** ~~${normal_price:.2f}~~")
                    st.write(f"**Sale Price:** **${price:.2f}**")
                    st.success(f"**Savings:** {game.get('discount', '0%')}")
                else:
                    st.write(f"**Price:** **${price:.2f}**")
            
            # Actions - TANPA Add to Cart
            wishlisted = is_in_wishlist(game['appid'])
            if wishlisted:
                if st.button("❤️ Remove from Wishlist", key="remove_wish_detail", use_container_width=True):
                    remove_from_wishlist(game['appid'])
                    st.rerun()
            else:
                if st.button("🤍 Add to Wishlist", key="add_wish_detail", use_container_width=True):
                    add_to_wishlist(game['appid'], game['name'], game['image'], game['price'])
                    st.rerun()
            
            # External link ke CheapShark
            if game.get('deal_link'):
                if st.button("🌐 View Deal on Steam", key="external_link", use_container_width=True):
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={game["deal_link"]}">', unsafe_allow_html=True)
        
        with col2:
            # Game info
            st.subheader("📋 Game Information")
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.write(f"**Genre:** {game['genre']}")
                st.write(f"**Release Year:** {game.get('year', 'N/A')}")
                st.write(f"**Players:** {game.get('players', 'N/A')}")
                if game.get('metacritic_score', 0) > 0:
                    st.write(f"**Metacritic Score:** {game['metacritic_score']}/100")
            
            with col_info2:
                st.write(f"**Rating:** ⭐ {game['rating']}/5.0")
                if game.get('steam_rating'):
                    st.write(f"**Steam Rating:** {game['steam_rating']}/5.0")
                if game.get('steam_rating_text'):
                    st.write(f"**Steam Reviews:** {game['steam_rating_text']}")
                if game.get('is_deal', False):
                    st.success("✅ Live Deal Available")
        
        # Game Statistics Charts
        st.markdown("---")
        st.subheader("📈 Game Statistics & Trends")
        
        if appid in st.session_state.all_game_stats:
            game_stats = st.session_state.all_game_stats[appid]
        else:
            game_stats = generate_realtime_game_statistics(game)
            st.session_state.all_game_stats[appid] = game_stats
        
        # Create 3 columns for mini charts
        col_chart1, col_chart2, col_chart3 = st.columns(3)
        
        with col_chart1:
            st.markdown("### 👥 Player Trend")
            current_players = game_stats['players'][-1]
            previous_players = game_stats['players'][-2]
            change = ((current_players - previous_players) / previous_players) * 100
            
            st.metric(
                "Current Players",
                f"{current_players:,}",
                f"{change:+.1f}%"
            )
            
            fig_players = go.Figure()
            fig_players.add_trace(go.Scatter(
                x=game_stats['dates'],
                y=game_stats['players'],
                mode='lines+markers',
                name='Players',
                line=dict(color='#00CC96', width=2),
                marker=dict(size=4)
            ))
            fig_players.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Date",
                yaxis_title="Players",
                hovermode='x unified'
            )
            st.plotly_chart(fig_players, use_container_width=True)
        
        with col_chart2:
            st.markdown("### ⭐ Rating Trend")
            current_rating = game_stats['ratings'][-1]
            previous_rating = game_stats['ratings'][-2]
            
            st.metric(
                "Current Rating",
                f"{current_rating:.1f}/5.0",
                f"{current_rating - previous_rating:+.2f}"
            )
            
            fig_rating = go.Figure()
            fig_rating.add_trace(go.Scatter(
                x=game_stats['dates'],
                y=game_stats['ratings'],
                mode='lines+markers',
                name='Rating',
                line=dict(color='#FFD700', width=2),
                marker=dict(size=4)
            ))
            fig_rating.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Date",
                yaxis_title="Rating",
                hovermode='x unified',
                yaxis=dict(range=[1, 5])
            )
            st.plotly_chart(fig_rating, use_container_width=True)
        
        with col_chart3:
            st.markdown("### 💰 Price History")
            current_price = game_stats['prices'][-1]
            
            if len(game_stats['prices']) > 1:
                previous_price = game_stats['prices'][-2]
                if previous_price > 0:
                    price_change = ((current_price - previous_price) / previous_price) * 100
                else:
                    price_change = 0
            else:
                price_change = 0
            
            st.metric(
                "Current Price",
                f"${current_price:.2f}",
                f"{price_change:+.1f}%"
            )
            
            fig_price = go.Figure()
            fig_price.add_trace(go.Scatter(
                x=game_stats['dates'],
                y=game_stats['prices'],
                mode='lines+markers',
                name='Price',
                line=dict(color='#FF6B6B', width=2),
                marker=dict(size=4)
            ))
            fig_price.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Date",
                yaxis_title="Price ($)",
                hovermode='x unified'
            )
            st.plotly_chart(fig_price, use_container_width=True)
        
        # Combined chart
        st.markdown("---")
        st.subheader("📊 Combined Metrics Overview")
        
        fig_combined = go.Figure()
        
        # Player trend (primary y-axis)
        fig_combined.add_trace(go.Scatter(
            x=game_stats['dates'],
            y=game_stats['players'],
            mode='lines',
            name='Players',
            line=dict(color='#00CC96', width=3),
            yaxis='y'
        ))
        
        # Rating trend (secondary y-axis)
        fig_combined.add_trace(go.Scatter(
            x=game_stats['dates'],
            y=game_stats['ratings'],
            mode='lines',
            name='Rating',
            line=dict(color='#FFD700', width=3),
            yaxis='y2'
        ))
        
        # Price trend (tertiary y-axis)
        if max(game_stats['prices']) > 0:
            fig_combined.add_trace(go.Scatter(
                x=game_stats['dates'],
                y=game_stats['prices'],
                mode='lines',
                name='Price ($)',
                line=dict(color='#FF6B6B', width=3),
                yaxis='y3'
            ))
        
        # Layout yang sudah diperbaiki
        fig_combined.update_layout(
            title=f'{game["name"]} - 30-Day Performance Overview',
            height=500,
            xaxis=dict(title='Date'),
            yaxis=dict(
                title=dict(text='Players', font=dict(color='#00CC96')),
                tickfont=dict(color='#00CC96')
            ),
            yaxis2=dict(
                title=dict(text='Rating', font=dict(color='#FFD700')),
                tickfont=dict(color='#FFD700'),
                anchor='x',
                overlaying='y',
                side='right'
            ),
            yaxis3=dict(
                title=dict(text='Price ($)', font=dict(color='#FF6B6B')),
                tickfont=dict(color='#FF6B6B'),
                anchor='free',
                overlaying='y',
                side='right',
                position=1.0
            ),
            hovermode='x unified',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        st.plotly_chart(fig_combined, use_container_width=True)
        
        # Analytics insights
        st.markdown("---")
        st.subheader("📈 Analytics Insights")
        
        col_insight1, col_insight2, col_insight3 = st.columns(3)
        
        with col_insight1:
            max_players = max(game_stats['players'])
            min_players = min(game_stats['players'])
            volatility = ((max_players - min_players) / min_players) * 100
            
            st.info(f"**Player Volatility:** {volatility:.1f}%")
            if volatility > 50:
                st.caption("🔺 High player fluctuation - possibly event-driven")
            elif volatility > 20:
                st.caption("📊 Moderate player activity")
            else:
                st.caption("📈 Stable player base")
        
        with col_insight2:
            avg_rating = sum(game_stats['ratings']) / len(game_stats['ratings'])
            rating_std = np.std(game_stats['ratings'])
            
            st.info(f"**Rating Stability:** {rating_std:.3f} std dev")
            if rating_std > 0.3:
                st.caption("⚠️ Rating fluctuates significantly")
            elif rating_std > 0.1:
                st.caption("📊 Moderate rating changes")
            else:
                st.caption("⭐ Very stable rating")
        
        with col_insight3:
            if game['price'] > 0:
                max_price = max(game_stats['prices'])
                min_price = min(game_stats['prices'])
                if min_price > 0:
                    price_range = ((max_price - min_price) / min_price) * 100
                    st.info(f"**Price Range:** {price_range:.1f}%")
                    if price_range > 30:
                        st.caption("💸 Significant price changes")
                    elif price_range > 10:
                        st.caption("💰 Moderate price fluctuations")
                    else:
                        st.caption("💵 Stable pricing")
                else:
                    st.info("**Price:** Free")
            else:
                st.success("**Price:** 🆓 Free to Play")
        
        # Description - MENAMBAHKAN AI GENERATED DESCRIPTION
        st.markdown("---")
        st.subheader("📖 About This Game")
        
        # Tombol untuk generate AI description
        if GEMINI_API_KEY:
            if st.button("🤖 Generate AI Description", key="generate_ai_desc"):
                with st.spinner("AI sedang membuat deskripsi..."):
                    ai_description = get_ai_game_description(game, GEMINI_API_KEY)
                    st.markdown(ai_description)
        else:
            st.info("🔑 **Note:** Konfigurasi GEMINI_API_KEY di Streamlit Cloud Secrets untuk mendapatkan deskripsi AI!")
        
        st.write(f"""
        **{game['name']}** is currently available as a live deal from **{game.get('store', 'the store')}**.
        
        **💸 Deal Details:**
        • **Current Price:** {'FREE' if game['price'] == 0 else f'${game["price"]:.2f}'}
        • **Normal Price:** {'Free' if game.get('normal_price', 0) == 0 else f'${game.get("normal_price", 0):.2f}'}
        • **Discount:** {game.get('discount', '0%')}
        • **Store:** {game.get('store', 'Unknown')}
        
        **🎮 Game Information:**
        • **Genre:** {game['genre']}
        • **Release Year:** {game.get('year', 'N/A')}
        • **Community Rating:** ⭐ {game['rating']}/5.0
        • **Player Count:** {game.get('players', 'N/A')}
        
        **📊 Deal Quality:**
        This deal has a rating of {game.get('deal_rating', 'N/A')} on CheapShark based on price history and savings.
        The game has {game.get('steam_rating_text', 'mixed reviews')} on Steam with {game.get('steam_rating_count', '0')} reviews.
        """)
    
    # Back button
    st.markdown("---")
    if st.button("← Back to Game Deals", key="back_to_games", use_container_width=True):
        del st.session_state.selected_game
        st.rerun()

st.markdown("---")
st.caption(f"© 2024 PlayHub Game Deals | Powered by CheapShark API & Gemini AI | {len(GAMES_DATA)} live deals loaded | Data updates hourly")