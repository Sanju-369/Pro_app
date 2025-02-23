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

# ✅ Secure Token Authentication
query_params = st.experimental_get_query_params()
token = query_params.get("token", [None])[0]

if not token:
    st.error("Unauthorized Access! Redirecting to login...")
    st.markdown('<meta http-equiv="refresh" content="2;url=https://login-sub-id.onrender.com/index.php">', unsafe_allow_html=True)
    st.stop()

# ✅ Validate Token with PHP Backend
php_validation_url = "https://yourwebsite.com/validate_token.php"
response = requests.get(f"{php_validation_url}?token={token}")

if response.status_code != 200 or response.text != "VALID":
    st.error("Invalid or Expired Session! Redirecting to login...")
    st.markdown('<meta http-equiv="refresh" content="2;url=https://yourwebsite.com/index.php">', unsafe_allow_html=True)
    st.stop()

# ✅ Define functions
def search_youtube_topic(topic, region):
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        st.error("❌ ERROR: YOUTUBE_API_KEY is missing.")
        return []

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {'part': 'snippet', 'q': topic, 'maxResults': 10, 'type': 'video', 'regionCode': region, 'key': api_key}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ ERROR: YouTube API request failed - {str(e)}")
        return []

    all_videos = []
    if 'items' in data:
        for item in data['items']:
            video_id = item['id'].get('videoId')
            if not video_id:
                continue

            all_videos.append({
                'title': item['snippet']['title'],
                'video_id': video_id,
                'video_url': f"https://www.youtube.com/watch?v={video_id}",
                'description': item['snippet'].get('description', 'No description available.')
            })
    
    return all_videos[:10]

def get_video_views(video_id):
    api_key = os.getenv("YOUTUBE_API_KEY")
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {'part': 'statistics', 'id': video_id, 'key': api_key}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ ERROR: Failed to fetch views for {video_id} - {str(e)}")
        return 0

    return int(data['items'][0]['statistics'].get('viewCount', 0)) if 'items' in data else 0

def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except:
        return "Transcript not available."

def function_1(region='IN', topic=''):
    st.write("✅ Fetching Top 5 Videos According to Views & Tags...") 
    trending_videos = search_youtube_topic(topic, region)
    if not trending_videos:
        st.warning("⚠️ No videos found. Exiting.")
        return [], "", ""

    all_content = ""
    titles = ""
    for video in trending_videos[:5]:  # Process top 5 videos
        video['views'] = get_video_views(video['video_id'])
        transcript = get_video_transcript(video['video_id'])
        if transcript == "Transcript not available.":
            transcript = video['description']  # Use description as fallback

        video['content'] = transcript
        all_content += f"### {video['title']} ({video['views']} views)\n{video['content']}\n\n"
        titles += f"{video['title']}, "
    
    trending_videos.sort(key=lambda x: x.get('views', 0), reverse=True)
    all_content = all_content[:20000]
    return trending_videos[:5], all_content, titles

def function1(all_content, titles):
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

def ai_researcher_chatbot(query):
    try:
        llm = ChatGroq(model="gemma2-9b-it")
        prompt = f"Answer the following question also ask some questions according to the topic: {query}"
        response = llm.invoke(prompt).content
        return response
    except Exception as e:
        return f"❌ ERROR: Failed to generate chatbot response - {str(e)}"

st.title("AI Agent for YouTube Research 🔍")
st.sidebar.header("Settings")

topic = st.sidebar.text_input("Topic", "india pak war 1971")
region = st.sidebar.selectbox("Region", ["IN", "US", "GB", "CA", "AU"], index=0)

if st.sidebar.button("Fetch Trending Videos"):
    trending_videos, all_content, titles = function_1(region=region, topic=topic)
    if trending_videos:
        st.subheader("Top Trending Videos")
        for i, video in enumerate(trending_videos, start=1):
            st.write(f"{i}. {video['title']} ({video['views']} views)")
            st.write(f"Video URL: [Link]({video['video_url']})")
            st.write(f"Description: {video['description']}")
            st.text_area(f"Transcript for {video['title']}", video['content'], height=150)
        st.subheader("YouTube Summarizer 📜")
        result = function1(all_content, titles)
        st.write("### Summary of the Above Videos")
        st.write(result)
    else:
        st.warning("⚠️ No trending videos found.")

st.sidebar.header("AI Researcher")
user_input = st.sidebar.text_area("Ask AI Researcher", "", height=100)

if st.sidebar.button("Ask"):
    if user_input:
        st.write("💬 **AI Researcher Response**")
        chatbot_response = ai_researcher_chatbot(user_input)
        st.write(chatbot_response)
    else:
        st.warning("⚠️ Please enter a question.")
