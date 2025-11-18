import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# Tambahkan path untuk import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.user_manager import UserManager

st.set_page_config(
    page_title="PlayHub - Home",
    page_icon="🎮",
    layout="wide"
)

# Check login status
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("⚠️ Please log in first!")
    if st.button("Go to Login"):
        st.switch_page("main.py")
else:
    st.title("🎮 PlayHub - Home")
    st.success(f"🎉 Welcome back, **{st.session_state.username}**!")

    # Fungsi untuk mendapatkan data Steam Charts (simulasi)
    def get_steam_charts_data():
        """
        Simulasi data Steam Charts trending games
        """
        try:
            # Data trending games (dalam ribuan pemain)
            trending_games = [
                {"Game": "Counter-Strike 2", "Current Players": 875.4, "Peak Today": 1250.2, "Change": "+5.2%", "Genre": "FPS", "Release": 2023},
                {"Game": "Dota 2", "Current Players": 652.1, "Peak Today": 890.7, "Change": "-2.1%", "Genre": "MOBA", "Release": 2013},
                {"Game": "PUBG: BATTLEGROUNDS", "Current Players": 423.8, "Peak Today": 567.3, "Change": "+1.8%", "Genre": "Battle Royale", "Release": 2017},
                {"Game": "Apex Legends", "Current Players": 387.6, "Peak Today": 512.9, "Change": "+3.4%", "Genre": "Battle Royale", "Release": 2019},
                {"Game": "Grand Theft Auto V", "Current Players": 245.3, "Peak Today": 321.8, "Change": "-0.7%", "Genre": "Action", "Release": 2015},
                {"Game": "Cyberpunk 2077", "Current Players": 198.7, "Peak Today": 245.6, "Change": "+8.9%", "Genre": "RPG", "Release": 2020},
                {"Game": "Baldur's Gate 3", "Current Players": 176.5, "Peak Today": 203.4, "Change": "+12.3%", "Genre": "RPG", "Release": 2023},
                {"Game": "Call of Duty", "Current Players": 154.2, "Peak Today": 198.7, "Change": "+2.1%", "Genre": "FPS", "Release": 2022},
                {"Game": "Rust", "Current Players": 132.8, "Peak Today": 167.9, "Change": "-1.2%", "Genre": "Survival", "Release": 2018},
                {"Game": "Team Fortress 2", "Current Players": 98.6, "Peak Today": 124.3, "Change": "+0.5%", "Genre": "FPS", "Release": 2007}
            ]
            
            return pd.DataFrame(trending_games)
        
        except Exception as e:
            st.error(f"Error getting Steam data: {e}")
            return pd.DataFrame()

    # Fungsi untuk membuat visualisasi
    def create_steam_visualizations(df):
        """Membuat berbagai visualisasi untuk data Steam"""
        
        # Bar chart players
        fig_players = px.bar(
            df.head(10),
            x='Game',
            y='Current Players',
            title='🎯 Current Players (in thousands)',
            color='Current Players',
            color_continuous_scale='viridis'
        )
        fig_players.update_layout(xaxis_tickangle=-45, showlegend=False)
        
        # Pie chart genre distribution
        genre_counts = df['Genre'].value_counts()
        fig_genre = px.pie(
            values=genre_counts.values,
            names=genre_counts.index,
            title='📊 Genre Distribution'
        )
        
        # Trend analysis
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df['Game'],
            y=df['Current Players'],
            mode='lines+markers',
            name='Current Players',
            line=dict(color='blue')
        ))
        fig_trend.add_trace(go.Scatter(
            x=df['Game'],
            y=df['Peak Today'],
            mode='lines+markers',
            name='Peak Today',
            line=dict(color='red')
        ))
        fig_trend.update_layout(title='📈 Players vs Peak Comparison')
        
        return fig_players, fig_genre, fig_trend
    
    # Tab untuk berbagai fitur
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Our Games", "🔥 Steam Charts", "📊 Analytics", "👤 Profile"])
    
    with tab1:
        st.subheader("Our Game Collection")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 🎯 Action Games")
            st.write("• **Adventure Quest** - Epic RPG adventure")
            st.write("• **Space Warriors** - Sci-fi FPS")
            st.write("• **Dragon Slayer** - Fantasy combat")
            if st.button("Play Action Games", key="action_play"):
                st.info("🚀 Loading action games...")
        
        with col2:
            st.markdown("### 🧩 Puzzle Games")
            st.write("• **Brain Teaser** - Mind challenges")
            st.write("• **Memory Master** - Memory tests")
            st.write("• **Logic Challenge** - Problem solving")
            if st.button("Play Puzzle Games", key="puzzle_play"):
                st.info("🧠 Loading puzzle games...")
        
        with col3:
            st.markdown("### 🏆 Sports Games")
            st.write("• **Soccer Pro** - Football simulation")
            st.write("• **Basketball Star** - NBA experience")
            st.write("• **Racing Extreme** - High-speed racing")
            if st.button("Play Sports Games", key="sports_play"):
                st.info("⚽ Loading sports games...")
        
        # Tombol back to login di bagian bawah tab 1
        st.markdown("---")
        if st.button("🔙 Back to Login Page", key="back_tab1", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.success("Returning to login page...")
            st.switch_page("main.py")
    
    with tab2:
        st.header("🔥 Steam Charts - Trending Games")
        
        # Refresh button dan tombol back
        col_refresh, col_back, col_stats = st.columns([1, 1, 2])
        with col_refresh:
            if st.button("🔄 Refresh Data", key="refresh_steam"):
                st.rerun()
        with col_back:
            if st.button("🔙 Back to Login", key="back_tab2"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.success("Returning to login page...")
                st.switch_page("main.py")
        with col_stats:
            st.info("📊 Real-time player statistics from Steam")
        
        # Get Steam data
        steam_data = get_steam_charts_data()
        
        if not steam_data.empty:
            # Metrics overview
            st.subheader("📈 Quick Stats")
            total_players = steam_data['Current Players'].sum()
            avg_players = steam_data['Current Players'].mean()
            top_game = steam_data.loc[steam_data['Current Players'].idxmax()]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Players", f"{total_players:,.0f}K")
            with col2:
                st.metric("Average per Game", f"{avg_players:.1f}K")
            with col3:
                st.metric("Top Game", top_game['Game'])
            with col4:
                st.metric("Top Game Players", f"{top_game['Current Players']}K")
            
            # Top games list
            st.subheader("🏆 Top 10 Trending Games")
            
            for i, game in steam_data.iterrows():
                with st.container():
                    gcol1, gcol2, gcol3, gcol4 = st.columns([2, 2, 1, 1])
                    with gcol1:
                        st.write(f"**#{i+1} {game['Game']}**")
                        st.caption(f"Genre: {game['Genre']} | Released: {game['Release']}")
                    with gcol2:
                        progress_val = min(game['Current Players'] / 10, 100)
                        st.progress(int(progress_val))
                        st.write(f"👥 {game['Current Players']}K / {game['Peak Today']}K")
                    with gcol3:
                        # Color code for change percentage
                        change_color = "green" if "+" in game['Change'] else "red"
                        st.markdown(f"<span style='color: {change_color}'>{game['Change']}</span>", 
                                  unsafe_allow_html=True)
                    # with gcol4:
                    #     if st.button("🎮 Play", key=f"play_{i}"):
                    #         st.success(f"Launching {game['Game']}...")
                    
                    st.markdown("---")
            
            # Visualizations
            st.subheader("📊 Data Visualizations")
            fig_players, fig_genre, fig_trend = create_steam_visualizations(steam_data)
            
            viz_col1, viz_col2 = st.columns(2)
            with viz_col1:
                st.plotly_chart(fig_players, use_container_width=True)
            with viz_col2:
                st.plotly_chart(fig_genre, use_container_width=True)
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Raw data table
            with st.expander("📋 View Raw Data"):
                st.dataframe(steam_data, use_container_width=True)
                
                # Download option
                csv = steam_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="steam_charts_data.csv",
                    mime="text/csv"
                )
        
        # Tombol back to login di bagian bawah tab 2
        st.markdown("---")
        if st.button("🔙 Back to Login Page", key="back_tab2_bottom", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.success("Returning to login page...")
            st.switch_page("main.py")
    
    with tab3:
        st.header("📊 Game Analytics")
        
        # Tombol back di analytics
        col_analytics, col_back_analytics = st.columns([3, 1])
        with col_back_analytics:
            if st.button("🔙 Back to Login", key="back_tab3"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.success("Returning to login page...")
                st.switch_page("main.py")
        
        st.subheader("Player Statistics")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Daily Active Users", "15,842", "+12%")
            st.metric("Average Session", "45 min", "+5%")
        
        with col2:
            st.metric("New Registrations", "324", "+8%")
            st.metric("Completion Rate", "78%", "+3%")
        
        # Sample analytics chart
        st.subheader("Player Engagement")
        sample_data = pd.DataFrame({
            'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'Players': [12000, 13500, 14200, 15800, 16800, 18500, 19400],
            'Sessions': [45000, 48000, 52000, 55000, 58000, 62000, 65000]
        })
        
        fig_engagement = px.line(sample_data, x='Day', y=['Players', 'Sessions'],
                               title='Weekly Player Engagement')
        st.plotly_chart(fig_engagement, use_container_width=True)
        
        # Tombol back to login di bagian bawah tab 3
        st.markdown("---")
        if st.button("🔙 Back to Login Page", key="back_tab3_bottom", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.success("Returning to login page...")
            st.switch_page("main.py")
    
    with tab4:
        st.header("👤 Your Profile")
        
        # Tombol back di profile
        col_profile, col_back_profile = st.columns([3, 1])
        with col_back_profile:
            if st.button("🔙 Back to Login", key="back_tab4"):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.success("Returning to login page...")
                st.switch_page("main.py")
        
        # Ambil data user dari JSON
        try:
            user_manager = UserManager()
            user_info = user_manager.get_user_info(st.session_state.username)
        except Exception as e:
            st.error(f"Error loading user data: {e}")
            user_info = None
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("pfp.jpeg", caption="Profile Picture", width=200)
            st.button("🖼️ Change Photo", key="change_photo", width=200)
        
        with col2:
            if user_info:
                st.write(f"**Username:** {user_info['username']}")
                st.write(f"**Email:** {user_info['email']}")
                st.write(f"**Member since:** {user_info['created_at'][:10]}")
                if user_info.get('last_login'):
                    st.write(f"**Last login:** {user_info['last_login'][:16]}")
                
            else:
                st.write(f"**Username:** {st.session_state.username}")
                st.write("**Member since:** January 2024")
        
        # Logout button dan back to login
        st.markdown("---")
        col_logout, col_back_final = st.columns(2)
        with col_logout:
            if st.button("🚪 Logout", type="primary", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.success("Logged out successfully!")
                st.switch_page("main.py")
        with col_back_final:
            if st.button("🔙 Back to Login Page", key="back_tab4_bottom", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.success("Returning to login page...")
                st.switch_page("main.py")

