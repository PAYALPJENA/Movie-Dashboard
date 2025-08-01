import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import random

# Helper to parse JSON-like columns
def parse_json_column(col):
    def safe_parse(x):
        try:
            if pd.notnull(x) and x.startswith('['):
                return [d['name'] for d in json.loads(x.replace("'", '"'))]
        except Exception:
            pass
        return []
    
    return col.apply(safe_parse)


@st.cache_data
def load_data():
    df = pd.read_csv('data/tmdb_5000_movies.csv')
    # Parse genres and production_companies columns
    df['genres_list'] = parse_json_column(df['genres'])
    df['companies_list'] = parse_json_column(df['production_companies'])
    df['release_year'] = pd.to_datetime(df['release_date'], errors='coerce').dt.year
    df['budget'] = pd.to_numeric(df['budget'], errors='coerce')
    df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce')
    df['runtime'] = pd.to_numeric(df['runtime'], errors='coerce')
    return df

df = load_data()

# Sidebar filters
st.sidebar.title("🎬 Movie Explorer")
st.sidebar.markdown("---")

# Year filter
year_min, year_max = int(df['release_year'].min()), int(df['release_year'].max())
years = st.sidebar.slider('Release Year', year_min, year_max, (year_min, year_max))

# Genre filter
all_genres = sorted({g for sublist in df['genres_list'] for g in sublist})
selected_genres = st.sidebar.multiselect('Genres', all_genres, default=all_genres[:5])

# Company filter
all_companies = sorted({c for sublist in df['companies_list'] for c in sublist})
selected_companies = st.sidebar.multiselect('Production Companies', all_companies, default=[])

# Rating filter
min_rating, max_rating = float(df['vote_average'].min()), float(df['vote_average'].max())
rating_range = st.sidebar.slider('IMDb Rating', min_rating, max_rating, (min_rating, max_rating))

# Filter data
filtered_df = df[
    (df['release_year'] >= years[0]) & (df['release_year'] <= years[1]) &
    (df['vote_average'] >= rating_range[0]) & (df['vote_average'] <= rating_range[1])
]
if selected_genres:
    filtered_df = filtered_df[filtered_df['genres_list'].apply(lambda x: any(g in x for g in selected_genres))]
if selected_companies:
    filtered_df = filtered_df[filtered_df['companies_list'].apply(lambda x: any(c in x for c in selected_companies))]

# Download button
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')
csv = convert_df_to_csv(filtered_df)
st.sidebar.download_button(
    label="📥 Download filtered data as CSV",
    data=csv,
    file_name='movies_filtered.csv',
    mime='text/csv',
)

# Main page
st.markdown('<div class="dashboard-title">🎬 Movie Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-subtitle">Interactive analytics for TMDB 5000 movies</div>', unsafe_allow_html=True)
st.markdown("## 📈 Overview Metrics")

metric_cols = st.columns(4)
with metric_cols[0]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(filtered_df):,}</div>
        <div class="metric-label">Total Movies</div>
    </div>
    """, unsafe_allow_html=True)
with metric_cols[1]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">${filtered_df['revenue'].sum()/1e9:.2f}B</div>
        <div class="metric-label">Total Revenue</div>
    </div>
    """, unsafe_allow_html=True)
with metric_cols[2]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{filtered_df['release_year'].nunique()}</div>
        <div class="metric-label">Years</div>
    </div>
    """, unsafe_allow_html=True)
with metric_cols[3]:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{filtered_df['vote_average'].mean():.1f}</div>
        <div class="metric-label">Avg. Rating</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "🎬 Movie Analysis", "💰 Revenue Insights", "🎭 Genre Trends", "📖 Data Storytelling"
])

with tab1:
    st.header("🎬 Movie Analysis")
    # Top 10 movies by revenue
    st.subheader("Top 10 Movies by Revenue")
    top10 = filtered_df.sort_values('revenue', ascending=False).head(10)
    fig_top10 = px.bar(
        top10,
        x='revenue',
        y='title',
        orientation='h',
        color='vote_average',
        labels={'revenue': 'Revenue', 'title': 'Movie Title', 'vote_average': 'Rating'},
        title='Top 10 Movies by Revenue',
        template='plotly_dark'
    )
    st.plotly_chart(fig_top10, use_container_width=True)

    # Ratings over time
    st.subheader("Average Rating Over Time")
    ratings_by_year = filtered_df.groupby('release_year')['vote_average'].mean().reset_index()
    fig_ratings = px.line(
        ratings_by_year,
        x='release_year',
        y='vote_average',
        labels={'release_year': 'Year', 'vote_average': 'Average Rating'},
        title='Average Movie Rating by Year',
        template='plotly_dark'
    )
    st.plotly_chart(fig_ratings, use_container_width=True)

with tab2:
    st.header("💰 Revenue Insights")
    # Revenue by year
    st.subheader("Revenue by Year")
    revenue_by_year = filtered_df.groupby('release_year')['revenue'].sum().reset_index()
    fig_rev_year = px.bar(
        revenue_by_year,
        x='release_year',
        y='revenue',
        labels={'release_year': 'Year', 'revenue': 'Revenue'},
        title='Total Revenue by Year',
        template='plotly_dark'
    )
    st.plotly_chart(fig_rev_year, use_container_width=True)

    # Revenue by company
    st.subheader("Top Production Companies by Revenue")
    company_revenue = (
        filtered_df.explode('companies_list')
        .groupby('companies_list')['revenue'].sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    fig_company = px.bar(
        company_revenue,
        x='revenue',
        y='companies_list',
        orientation='h',
        labels={'revenue': 'Revenue', 'companies_list': 'Company'},
        title='Top 10 Production Companies by Revenue',
        template='plotly_dark'
    )
    st.plotly_chart(fig_company, use_container_width=True)

with tab3:
    st.header("🎭 Genre Trends")
    # Genre popularity
    st.subheader("Most Popular Genres")
    genre_counts = (
        filtered_df.explode('genres_list')
        .groupby('genres_list')['title'].count()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
        .rename(columns={'title': 'Movie Count'})
    )
    fig_genre = px.bar(
        genre_counts,
        x='Movie Count',
        y='genres_list',
        orientation='h',
        labels={'genres_list': 'Genre'},
        title='Top 10 Genres by Movie Count',
        template='plotly_dark'
    )
    st.plotly_chart(fig_genre, use_container_width=True)

    # Genre revenue
    st.subheader("Genre Revenue")
    genre_revenue = (
        filtered_df.explode('genres_list')
        .groupby('genres_list')['revenue'].sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    fig_genre_rev = px.bar(
        genre_revenue,
        x='revenue',
        y='genres_list',
        orientation='h',
        labels={'genres_list': 'Genre', 'revenue': 'Revenue'},
        title='Top 10 Genres by Revenue',
        template='plotly_dark'
    )
    st.plotly_chart(fig_genre_rev, use_container_width=True)

with tab4:
    st.header("📖 Data Storytelling")
    st.markdown("""
    <div class="story-header">🎬 The Evolution of Blockbuster Movies</div>
    <div class="story-text">
    Explore how movie genres, budgets, and revenues have changed over time. 
    The rise of superhero and fantasy genres, the dominance of major studios, and the impact of high budgets on box office success are all visible in the data.
    </div>
    """, unsafe_allow_html=True)

    # Fun facts
    fun_facts = [
        f"The highest-grossing movie is '{df.loc[df['revenue'].idxmax()]['title']}' with ${df['revenue'].max():,.0f} revenue!",
        f"The most common genre is '{genre_counts.iloc[0]['genres_list']}' with {genre_counts.iloc[0]['Movie Count']} movies.",
        f"The average movie runtime is {df['runtime'].mean():.1f} minutes.",
        f"The oldest movie in the dataset is from {df['release_year'].min()}.",
        f"The most productive year was {df['release_year'].value_counts().idxmax()} with {df['release_year'].value_counts().max()} movies released.",
        f"The company with the highest total revenue is '{company_revenue.iloc[0]['companies_list']}'."
    ]
    if st.button("🎬 Generate Random Movie Fact"):
        st.success(random.choice(fun_facts))