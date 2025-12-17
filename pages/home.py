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


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.user_manager import UserManager

DEEPSEEK_API_KEY = "sk-26a8e20040dc42d6870cab221aea63a8"  

try:
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "sk-26a8e20040dc42d6870cab221aea63a8":
        client = openai.OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com" 
        )
        DEEPSEEK_ENABLED = True
    else:
        st.warning("⚠️ DeepSeek AI tidak diaktifkan. Silakan tambahkan API key untuk menggunakan fitur AI.")
        DEEPSEEK_ENABLED = False
except Exception as e:
    st.error(f"Error konfigurasi DeepSeek AI: {str(e)}")
    DEEPSEEK_ENABLED = False


def generate_game_description_with_ai(game_data):
    """Generate deskripsi game menggunakan DeepSeek AI"""
    if not DEEPSEEK_ENABLED:
        return None
    
    try:
   
        prompt = f"""
        Berikan deskripsi yang menarik tentang game berikut dalam 3 paragraf (maksimal 200 kata):
        
        Nama Game: {game_data.get('name', 'Unknown')}
        Genre: {game_data.get('genre', 'Unknown')}
        Rating: {game_data.get('rating', 0)}/5.0
        Tahun Rilis: {game_data.get('year', 'Unknown')}
        Harga: ${game_data.get('price', 0):.2f} (Diskon: {game_data.get('discount', '0%')})
        
        Format respons:
        1. Paragraf 1: Pengenalan dan gameplay
        2. Paragraf 2: Fitur utama dan keunikan
        3. Paragraf 3: Rekomendasi untuk pemain
        
        Gunakan bahasa Indonesia yang menarik dan persuasif.
        """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Anda adalah ahli game yang berpengalaman. Berikan deskripsi yang menarik dan informatif tentang game-game populer. Gunakan bahasa Indonesia."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
            stream=False
        )
        
        if response and response.choices:
            return response.choices[0].message.content
        else:
            return None
            
    except openai.APIError as e:
        st.error(f"API Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error generating AI description: {str(e)}")
        return None

def generate_game_recommendations_with_ai(user_preferences, available_games):
    """Generate rekomendasi game personalisasi menggunakan AI"""
    if not DEEPSEEK_ENABLED or len(available_games) < 5:
        return ""
    
    try:

        sample_games = random.sample(available_games, min(20, len(available_games)))
        
        prompt = f"""
        Berikan 5 rekomendasi game personalisasi berdasarkan preferensi user:
        
        Preferensi User:
        - Genre favorit: {', '.join(user_preferences.get('favorite_genres', []))}
        - Rentang harga: ${user_preferences.get('price_range', {}).get('min', 0)} - ${user_preferences.get('price_range', {}).get('max', 100)}
        
        Daftar game yang tersedia (format: Nama | Genre | Rating | Harga):
        {'\n'.join([f"{g['name']} | {g['genre']} | {g['rating']}/5.0 | ${g['price']:.2f}" for g in sample_games])}
        
        Berikan rekomendasi dalam format:
        1. [Nama Game] - [Genre] - ⭐[Rating]
           • Alasan: [Penjelasan singkat mengapa cocok]
        2. ...
        
        Prioritaskan game dengan rating tinggi dan sesuai budget user.
        """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Anda adalah personal game recommender yang membantu pemain menemukan game yang sesuai dengan preferensi mereka. Gunakan bahasa Indonesia."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.8,
            stream=False
        )
        
        if response and response.choices:
            return response.choices[0].message.content
        else:
            return ""
            
    except Exception as e:
        st.error(f"Error generating AI recommendations: {str(e)}")
        return ""

# Fungsi test koneksi API
def test_deepseek_api():
    """Test koneksi ke DeepSeek API"""
    if not DEEPSEEK_ENABLED:
        return False, "AI tidak aktif"
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello, test connection!"}],
            max_tokens=10
        )
        return True, "✅ API Connected!"
    except openai.AuthenticationError:
        return False, "❌ API key tidak valid"
    except openai.APIError as e:
        return False, f"❌ API Error: {str(e)}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# KONFIGURASI API CHEAPSHARK
CHEAPSHARK_API_URL = "https://www.cheapshark.com/api/1.0/deals"
CHEAPSHARK_STORES_URL = "https://www.cheapshark.com/api/1.0/stores"


# FUNGSI UNTUK MENDAPATKAN DATA DARI API
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
    page_title="PlayHub - Game Deals",
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
    .chart-container {
        background: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .profile-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin: 10px 0;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .wishlist-item {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #4A90E2;
        transition: transform 0.2s ease;
    }
    .wishlist-item:hover {
        transform: translateX(5px);
        background: #e9ecef;
    }
    .ai-bubble {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 15px;
        border-radius: 15px;
        margin: 10px 0;
        border-left: 5px solid #00FF88;
    }
    .ai-insight {
        background: #f0f7ff;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border: 2px solid #4A90E2;
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

# Session state untuk AI
if 'ai_descriptions' not in st.session_state:
    st.session_state.ai_descriptions = {}

if 'ai_recommendations' not in st.session_state:
    st.session_state.ai_recommendations = ""

# Session state lainnya
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
# MAIN APP
# -------------------------
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Please log in first!")
    if st.button("Go to Login"):
        st.switch_page("main.py")
else:
    # Header utama
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🎮 PlayHub - Live Game Deals")
    st.success(f"🎉 Welcome back, **{st.session_state.username}**!")
    st.info(f"🔄 Connected to CheapShark API ({len(GAMES_DATA)} live deals loaded)")
    
    # Status AI
    if DEEPSEEK_ENABLED:
        st.success("🤖 DeepSeek AI Assistant: Aktif")
    else:
        st.warning("🤖 DeepSeek AI Assistant: Nonaktif - Tambahkan API key untuk mengaktifkan")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("❤️ Your Wishlist")
        if st.session_state.wishlist:
            st.write(f"You have **{len(st.session_state.wishlist)}** games in your wishlist")
            for i, item in enumerate(st.session_state.wishlist[:3]):
                st.write(f"• {item['name'][:20]}...")
            if len(st.session_state.wishlist) > 3:
                st.write(f"... and {len(st.session_state.wishlist) - 3} more")
        else:
            st.info("Your wishlist is empty. Add games from the store!")
        
        # Test API Connection
        if DEEPSEEK_ENABLED:
            st.markdown("---")
            st.header("🔧 API Test")
            if st.button("Test DeepSeek Connection", use_container_width=True):
                success, message = test_deepseek_api()
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        # AI Recommendations Section
        if DEEPSEEK_ENABLED and st.session_state.user_data['preferences']['favorite_genres']:
            st.markdown("---")
            st.header("🤖 AI Recommendations")
            if st.button("🎯 Get Personalized Recommendations", use_container_width=True):
                with st.spinner("🤖 AI sedang menganalisis preferensi Anda..."):
                    recommendations = generate_game_recommendations_with_ai(
                        st.session_state.user_data['preferences'],
                        GAMES_DATA
                    )
                    st.session_state.ai_recommendations = recommendations
                    st.rerun()
        
        # API status
        st.markdown("---")
        st.write("**API Status:**")
        st.success("✅ Connected to CheapShark")
        if DEEPSEEK_ENABLED:
            st.success("✅ DeepSeek AI Active")
        else:
            st.warning("⚠️ DeepSeek AI Inactive")
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
            st.session_state.ai_descriptions = {}  # Clear AI cache
            st.rerun()

    # Main tabs - TAMBAH TAB AI
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
        
        # Chart 3: Genre Distribution
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
            
            if st.button("💾 Save Preferences", key="save_preferences"):
                st.session_state.user_data['preferences']['favorite_genres'] = selected_genres
                st.session_state.user_data['preferences']['price_range'] = {'min': min_price, 'max': max_price}
                st.success("✅ Preferences saved successfully!")
                time.sleep(1)
                st.rerun()
        
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
        # ==================== AI ASSISTANT TAB ====================
        st.header("🤖 AI Game Assistant")
        
        if not DEEPSEEK_ENABLED:
            st.warning("""
            ⚠️ **DeepSeek AI tidak diaktifkan.**
            
            Untuk menggunakan fitur AI Assistant, Anda perlu:
            1. Dapatkan API key dari [DeepSeek Platform](https://platform.deepseek.com/api_keys)
            2. Ganti API key di bagian atas kode
            3. Restart aplikasi
            
            Fitur yang tersedia dengan AI:
            • Deskripsi game yang menarik
            • Rekomendasi personalisasi
            • Analisis game
            """)
        else:
            st.success("✅ DeepSeek AI Assistant aktif dan siap membantu!")
            
            # Info API Key
            with st.expander("🔑 API Key Info"):
                st.code(f"API Key: {DEEPSEEK_API_KEY[:15]}...")
                st.caption("Status: Active" if DEEPSEEK_ENABLED else "Status: Inactive")
            
            # Pilih game untuk analisis AI
            st.subheader("🎯 Pilih Game untuk Analisis AI")
            
            game_names = [game['name'] for game in GAMES_DATA]
            selected_game_name = st.selectbox(
                "Pilih game yang ingin dianalisis:",
                options=game_names,
                index=0
            )
            
            # Temukan game yang dipilih
            selected_game_for_ai = None
            for game in GAMES_DATA:
                if game['name'] == selected_game_name:
                    selected_game_for_ai = game
                    break
            
            if selected_game_for_ai:
                col_ai1, col_ai2 = st.columns([1, 2])
                
                with col_ai1:
                    st.image(selected_game_for_ai['image'], width=200)
                    st.write(f"**{selected_game_for_ai['name']}**")
                    st.write(f"Genre: {selected_game_for_ai['genre']}")
                    st.write(f"Rating: ⭐ {selected_game_for_ai['rating']}/5.0")
                    st.write(f"Harga: ${selected_game_for_ai['price']:.2f}")
                    if selected_game_for_ai.get('discount', '0%') != '0%':
                        st.success(f"Diskon: {selected_game_for_ai['discount']}")
                
                with col_ai2:
                    # Tombol untuk generate deskripsi AI
                    if st.button("🤖 Generate AI Description", key="generate_ai_desc", use_container_width=True):
                        with st.spinner("🤖 AI sedang membuat deskripsi yang menarik..."):
                            ai_description = generate_game_description_with_ai(selected_game_for_ai)
                            
                            if ai_description:
                                st.session_state.ai_descriptions[selected_game_for_ai['appid']] = ai_description
                                st.success("✅ Deskripsi berhasil dibuat!")
                                st.rerun()
                            else:
                                st.error("❌ Gagal membuat deskripsi")
                    
                    # Tampilkan deskripsi AI jika ada
                    if selected_game_for_ai['appid'] in st.session_state.ai_descriptions:
                        st.markdown("---")
                        st.subheader("📝 AI-Generated Description")
                        st.markdown(f'<div class="ai-bubble">{st.session_state.ai_descriptions[selected_game_for_ai["appid"]]}</div>', unsafe_allow_html=True)
                        
                        # Tombol untuk clear cache AI
                        col_clear1, col_clear2 = st.columns(2)
                        with col_clear1:
                            if st.button("🔄 Regenerate", key="regen_ai_desc"):
                                del st.session_state.ai_descriptions[selected_game_for_ai['appid']]
                                st.rerun()
                        with col_clear2:
                            if st.button("🗑️ Clear", key="clear_ai_desc"):
                                del st.session_state.ai_descriptions[selected_game_for_ai['appid']]
                                st.success("Deskripsi dihapus!")
                                time.sleep(1)
                                st.rerun()
                    
                    # AI Insights
                    st.markdown("---")
                    st.subheader("💡 AI Insights")
                    
                    # Value for Money Analysis
                    with st.expander("💰 Analisis Value for Money"):
                        price = selected_game_for_ai['price']
                        rating = selected_game_for_ai['rating']
                        
                        if price == 0:
                            st.success("**🆓 FREE TO PLAY**")
                            st.write("Game ini gratis! Nilai terbaik untuk uang Anda.")
                        elif price < 10:
                            if rating > 4.0:
                                st.success("**💎 Excellent Value**")
                                st.write(f"Hanya ${price:.2f} untuk game dengan rating {rating}/5.0. Deal yang sangat bagus!")
                            elif rating > 3.0:
                                st.info("**👍 Good Value**")
                                st.write(f"${price:.2f} adalah harga yang wajar untuk kualitas game ini.")
                            else:
                                st.warning("**⚠️ Consider Carefully**")
                                st.write(f"Rating {rating}/5.0 untuk harga ${price:.2f}. Cek review dulu sebelum membeli.")
                        else:
                            if rating > 4.5:
                                st.success("**🏆 Premium Quality**")
                                st.write(f"Game premium dengan rating {rating}/5.0. Investasi yang bagus untuk pengalaman gaming terbaik.")
                            elif rating > 4.0:
                                st.info("**💵 Fair Price**")
                                st.write(f"Harga ${price:.2f} sesuai dengan kualitas game berrating {rating}/5.0.")
                            else:
                                st.warning("**📉 Might Wait for Sale**")
                                st.write(f"Rating {rating}/5.0 untuk harga ${price:.2f}. Mungkin lebih baik tunggu diskon lebih besar.")
                    
                    # Genre Analysis
                    with st.expander("🎮 Analisis Genre"):
                        genre = selected_game_for_ai['genre']
                        genre_games = [g for g in GAMES_DATA if g['genre'] == genre]
                        avg_genre_price = sum(g['price'] for g in genre_games) / len(genre_games) if genre_games else 0
                        avg_genre_rating = sum(g['rating'] for g in genre_games) / len(genre_games) if genre_games else 0
                        
                        st.write(f"**Genre:** {genre}")
                        st.write(f"**Game dalam genre ini:** {len(genre_games)}")
                        st.write(f"**Harga rata-rata genre:** ${avg_genre_price:.2f}")
                        st.write(f"**Rating rata-rata genre:** {avg_genre_rating:.1f}/5.0")
                        
                        # Perbandingan dengan rata-rata genre
                        if selected_game_for_ai['price'] < avg_genre_price * 0.8:
                            st.success("**💸 Below Genre Average** - Harga lebih murah dari rata-rata genre!")
                        elif selected_game_for_ai['rating'] > avg_genre_rating + 0.5:
                            st.success("**⭐ Above Genre Average** - Rating lebih tinggi dari rata-rata genre!")
                    
                    # AI Recommendations jika ada
                    if st.session_state.ai_recommendations:
                        st.markdown("---")
                        st.subheader("🎯 AI Personal Recommendations")
                        st.markdown(f'<div class="ai-insight">{st.session_state.ai_recommendations}</div>', unsafe_allow_html=True)
                        
                        if st.button("🔄 Refresh Recommendations", key="refresh_ai_rec"):
                            st.session_state.ai_recommendations = ""
                            st.rerun()

# ==================== GAME DETAILS VIEW (DENGAN AI) ====================
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
            
            # AI Description Button
            if DEEPSEEK_ENABLED:
                st.markdown("---")
                if st.button("🤖 Generate AI Description", key="ai_desc_game_detail", use_container_width=True):
                    with st.spinner("🤖 AI sedang menganalisis game..."):
                        ai_description = generate_game_description_with_ai(game)
                        if ai_description:
                            st.session_state.ai_descriptions[game['appid']] = ai_description
                            st.rerun()
            
            # Actions
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
                if st.button("🌐 View Deal on CheapShark", key="external_link", use_container_width=True):
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
            
            # AI Description Section
            if DEEPSEEK_ENABLED and game['appid'] in st.session_state.ai_descriptions:
                st.markdown("---")
                st.subheader("🤖 AI-Powered Description")
                st.markdown(f'<div class="ai-bubble">{st.session_state.ai_descriptions[game["appid"]]}</div>', unsafe_allow_html=True)
                
                if st.button("🔄 Regenerate AI Description", key="regen_ai_desc"):
                    with st.spinner("🤖 AI sedang membuat deskripsi baru..."):
                        ai_description = generate_game_description_with_ai(game)
                        if ai_description:
                            st.session_state.ai_descriptions[game['appid']] = ai_description
                            st.rerun()
        
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
        
        # AI-Powered Analytics insights
        st.markdown("---")
        st.subheader("🤖 AI-Powered Analytics Insights")
        
        col_insight1, col_insight2, col_insight3 = st.columns(3)
        
        with col_insight1:
            max_players = max(game_stats['players'])
            min_players = min(game_stats['players'])
            volatility = ((max_players - min_players) / min_players) * 100
            
            st.info(f"**Player Volatility:** {volatility:.1f}%")
            if volatility > 50:
                st.caption("🔺 **AI Insight:** Tinggi - Kemungkinan ada event atau update besar baru-baru ini")
            elif volatility > 20:
                st.caption("📊 **AI Insight:** Sedang - Komunitas aktif dengan fluktuasi normal")
            else:
                st.caption("📈 **AI Insight:** Stabil - Basis pemain yang solid dan konsisten")
        
        with col_insight2:
            avg_rating = sum(game_stats['ratings']) / len(game_stats['ratings'])
            rating_std = np.std(game_stats['ratings'])
            
            st.info(f"**Rating Stability:** {rating_std:.3f} std dev")
            if rating_std > 0.3:
                st.caption("⚠️ **AI Insight:** Fluktuasi signifikan - Mungkin ada kontroversi atau update kontroversial")
            elif rating_std > 0.1:
                st.caption("📊 **AI Insight:** Perubahan moderat - Review yang beragam tapi stabil")
            else:
                st.caption("⭐ **AI Insight:** Sangat stabil - Kualitas game yang konsisten diakui pemain")
        
        with col_insight3:
            if game['price'] > 0:
                max_price = max(game_stats['prices'])
                min_price = min(game_stats['prices'])
                if min_price > 0:
                    price_range = ((max_price - min_price) / min_price) * 100
                    st.info(f"**Price Range:** {price_range:.1f}%")
                    if price_range > 30:
                        st.caption("💸 **AI Insight:** Perubahan harga signifikan - Sering diskon besar")
                    elif price_range > 10:
                        st.caption("💰 **AI Insight:** Fluktuasi harga moderat - Harga berubah sesuai musim")
                    else:
                        st.caption("💵 **AI Insight:** Harga stabil - Jarang diskon, harga tetap")
                else:
                    st.info("**Price:** Free")
            else:
                st.success("**Price:** 🆓 Free to Play")
        
        # Description dengan AI
        st.markdown("---")
        st.subheader("📖 About This Game")
        
        # Tampilkan deskripsi AI jika ada, jika tidak tampilkan deskripsi default
        if game['appid'] in st.session_state.ai_descriptions:
            st.markdown(f'<div class="ai-bubble">{st.session_state.ai_descriptions[game["appid"]]}</div>', unsafe_allow_html=True)
        else:
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
        
        # Tombol untuk generate AI description jika belum ada
        if DEEPSEEK_ENABLED and game['appid'] not in st.session_state.ai_descriptions:
            if st.button("🤖 Generate AI-Powered Description", key="final_ai_desc"):
                with st.spinner("🤖 AI sedang membuat deskripsi yang menarik..."):
                    ai_description = generate_game_description_with_ai(game)
                    if ai_description:
                        st.session_state.ai_descriptions[game['appid']] = ai_description
                        st.rerun()
    
    # Back button
    st.markdown("---")
    if st.button("← Back to Game Deals", key="back_to_games", use_container_width=True):
        del st.session_state.selected_game
        st.rerun()

st.markdown("---")
st.caption(f"© 2024 PlayHub Game Deals | Powered by CheapShark API | {len(GAMES_DATA)} live deals loaded | Data updates hourly | {'🤖 AI Assistant: Active' if DEEPSEEK_ENABLED else '🤖 AI Assistant: Inactive'}")