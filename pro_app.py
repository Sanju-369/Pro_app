import os
import requests
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Secure UI: Hide Streamlit menu, footer, and GitHub edit button
st.set_page_config(page_title="Secure App", page_icon="🔒", layout="wide")

st.markdown("""
    <style>
    #MainMenu, header, footer {visibility: hidden;}
    [title="Edit source"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
youtube_api_key = os.getenv("YOUTUBE_API_KEY")

import streamlit as st
import requests

# ✅ Step 1: Initialize session state variables (Prevents "AttributeError")
if "token" not in st.session_state:
    st.session_state["token"] = None  # Ensure token is initialized
if "redirected" not in st.session_state:
    st.session_state["redirected"] = False  # Prevent multiple redirects

# ✅ Step 2: Retrieve token from URL parameters (only if not already set)
query_params = st.query_params
token = query_params.get("token", [None])[0]

if token and st.session_state["token"] is None:
    st.session_state["token"] = token  # Store token persistently

# ✅ Step 3: Use stored token for validation
token = st.session_state["token"]

if not token:
    if not st.session_state["redirected"]:  # Prevent infinite redirection
        st.session_state["redirected"] = True
        st.error("Unauthorized Access! Redirecting to login...")
        st.markdown('<meta http-equiv="refresh" content="2;url=https://login-sub-id.onrender.com">', unsafe_allow_html=True)
    st.stop()

# ✅ Step 4: Validate Token with PHP Backend (with error handling)
php_validation_url = "https://login-sub-id.onrender.com/validate_token.php"

try:
    response = requests.get(f"{php_validation_url}?token={token}", timeout=5)  # Prevents hanging requests
    response_text = response.text.strip()
except requests.RequestException:
    response_text = "ERROR"

if response.status_code != 200 or response_text != "VALID":
    if not st.session_state["redirected"]:  # Prevent infinite redirection
        st.session_state["redirected"] = True
        st.session_state["token"] = None  # Clear invalid token
        st.error("Invalid or Expired Session! Redirecting to login...")
        st.markdown('<meta http-equiv="refresh" content="2;url=https://login-sub-id.onrender.com/index.php">', unsafe_allow_html=True)
    st.stop()

st.success("Welcome to the Dashboard! You are authenticated.")

# ✅ Define functions
def search_youtube_topic(topic, region):
    """Fetch trending YouTube videos for a given topic and region."""
    if not youtube_api_key:
        st.error("❌ ERROR: YOUTUBE_API_KEY is missing.")
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {'part': 'snippet', 'q': topic, 'maxResults': 10, 'type': 'video', 'regionCode': region, 'key': youtube_api_key}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ ERROR: YouTube API request failed - {str(e)}")
        return []

    videos = []
    for item in data.get('items', []):
        video_id = item['id'].get('videoId')
        if not video_id:
            continue

        videos.append({
            'title': item['snippet']['title'],
            'video_id': video_id,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'description': item['snippet'].get('description', 'No description available.')
        })
    
    return videos[:10]

def get_video_views(video_id):
    """Retrieve the view count of a YouTube video."""
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {'part': 'statistics', 'id': video_id, 'key': youtube_api_key}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ ERROR: Failed to fetch views for {video_id} - {str(e)}")
        return 0

    return int(data.get('items', [{}])[0].get('statistics', {}).get('viewCount', 0))

def get_video_transcript(video_id):
    """Fetch transcript of a YouTube video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except:
        return "Transcript not available."

def fetch_trending_videos(region='IN', topic=''):
    """Fetch top 5 trending videos and extract transcripts."""
    st.write("✅ Fetching Top 5 Videos According to Views & Tags...") 
    videos = search_youtube_topic(topic, region)
    if not videos:
        st.warning("⚠️ No videos found. Exiting.")
        return [], "", ""

    all_content = ""
    titles = ""
    for video in videos[:5]:  # Process top 5 videos
        video['views'] = get_video_views(video['video_id'])
        transcript = get_video_transcript(video['video_id'])
        if transcript == "Transcript not available.":
            transcript = video['description']  # Use description as fallback

        video['content'] = transcript
        all_content += f"### {video['title']} ({video['views']} views)\n{video['content']}\n\n"
        titles += f"{video['title']}, "
    
    videos.sort(key=lambda x: x.get('views', 0), reverse=True)
    return videos[:5], all_content[:20000], titles

def generate_summary(all_content, titles):
    """Generate AI-powered summary based on video content."""
    if not all_content.strip():
        st.warning("⚠️ No transcripts found. Using only titles for AI generation.")
        prompt = f"Generate an engaging article using these video titles: {titles}."
    else:
        prompt = f"Write a high-quality summary for these videos: {titles}.\n\n{all_content}"

    try:
        llm = ChatGroq(model="gemma2-9b-it")
        response = llm.invoke(prompt).content
        return response if response else "⚠️ AI content generation failed."
    except Exception as e:
        st.error(f"\n❌ ERROR: AI Model Call Failed - {str(e)}")
        return "⚠️ AI content generation failed. Please try again."

def ai_research_chat(query):
    """AI chatbot that answers questions and suggests related topics."""
    try:
        llm = ChatGroq(model="gemma2-9b-it")
        prompt = f"Answer this question and suggest related questions: {query}"
        response = llm.invoke(prompt).content
        return response
    except Exception as e:
        return f"❌ ERROR: Failed to generate chatbot response - {str(e)}"

# 🎯 **Streamlit UI**
st.title("AI Agent for YouTube Research 🔍")
st.sidebar.header("Settings")

topic = st.sidebar.text_input("Topic", "india pak war 1971")
region = st.sidebar.selectbox("Region", ["IN", "US", "GB", "CA", "AU"], index=0)

if st.sidebar.button("Fetch Trending Videos"):
    trending_videos, all_content, titles = fetch_trending_videos(region=region, topic=topic)
    if trending_videos:
        st.subheader("Top Trending Videos")
        for i, video in enumerate(trending_videos, start=1):
            st.write(f"{i}. {video['title']} ({video['views']} views)")
            st.write(f"Video URL: [Link]({video['video_url']})")
            st.write(f"Description: {video['description']}")
            st.text_area(f"Transcript for {video['title']}", video['content'], height=150)
        st.subheader("YouTube Summarizer 📜")
        result = generate_summary(all_content, titles)
        st.write("### Summary of the Above Videos")
        st.write(result)
    else:
        st.warning("⚠️ No trending videos found.")

st.sidebar.header("AI Researcher")
user_input = st.sidebar.text_area("Ask AI Researcher", "", height=100)

if st.sidebar.button("Ask"):
    if user_input:
        st.write("💬 **AI Researcher Response**")
        chatbot_response = ai_research_chat(user_input)
        st.write(chatbot_response)
    else:
        st.warning("⚠️ Please enter a question.")
