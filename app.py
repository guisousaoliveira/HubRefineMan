import os
import time
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

BRANDS = {
    "alpha_dominus": {
        "yt_id": "UCvvcvvdlLiCS6zKs_RUSVtw",
        "tk_username": "alphadominus.tv"
    },
    "frequencia_mental": {
        "yt_id": "UCT9w5tFL3UxrCVDkTUHF_jQ",
        "tk_username": "afrequenciamental"
    }
}

app_cache = {"data": None, "last_updated": 0}
CACHE_DURATION = 1800 

def get_tiktok_data(username):
    """Busca perfil e os 3 últimos vídeos do TikTok"""
    if not RAPIDAPI_KEY: return {}
    
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY, 
        "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
    }
    
    # 1. Busca Perfil
    profile_data = {"followers": "0", "likes": "0", "videoCount": "0", "recentVideos": []}
    try:
        res_profile = requests.get("https://tiktok-scraper7.p.rapidapi.com/user/info", headers=headers, params={"unique_id": username})
        stats = res_profile.json().get('data', {}).get('stats', {})
        profile_data["followers"] = str(stats.get('followerCount', '0'))
        profile_data["likes"] = str(stats.get('heartCount', '0'))
        profile_data["videoCount"] = str(stats.get('videoCount', '0'))
    except Exception as e:
        print(f"Erro perfil TK {username}: {e}")

    # 2. Busca Vídeos Recentes
    try:
        res_videos = requests.get("https://tiktok-scraper7.p.rapidapi.com/user/posts", headers=headers, params={"unique_id": username, "count": "3", "cursor": "0"})
        videos_list = res_videos.json().get('data', {}).get('videos', [])[:3]
        
        recent_videos = []
        for v in videos_list:
            recent_videos.append({
                "title": v.get('title', ''),
                "thumbnail": v.get('cover', ''),
                "videoId": v.get('video_id', ''),
                "views": str(v.get('play_count', '0')),
                "likes": str(v.get('digg_count', '0')),
                "url": f"https://www.tiktok.com/@{username}/video/{v.get('video_id')}"
            })
        profile_data["recentVideos"] = recent_videos
    except Exception as e:
        print(f"Erro vídeos TK {username}: {e}")

    return profile_data

def get_youtube_data(channel_id):
    """Puxa dados e vídeos do YouTube com tratamento de erro reforçado"""
    try:
        url_ch = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet,contentDetails&id={channel_id}&key={YOUTUBE_API_KEY}"
        data = requests.get(url_ch).json()
        
        if 'items' not in data: return {} # Evita quebrar se a cota exceder
        
        item = data['items'][0]
        stats = item['statistics']
        snippet = item['snippet']
        
        playlist_id = item['contentDetails']['relatedPlaylists']['uploads']
        url_vids = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={playlist_id}&maxResults=3&key={YOUTUBE_API_KEY}"
        vids_data = requests.get(url_vids).json()
        
        recent_videos = []
        video_ids = []
        
        for v in vids_data.get('items', []):
            vid_id = v['snippet']['resourceId']['videoId']
            video_ids.append(vid_id)
            recent_videos.append({
                "title": v['snippet']['title'],
                "thumbnail": v['snippet']['thumbnails']['medium']['url'],
                "videoId": vid_id,
                "views": "0", "likes": "0",
                "url": f"https://youtube.com/watch?v={vid_id}"
            })
            
        # Segunda chamada para pegar views/likes (Se falhar, mantém "0")
        if video_ids:
            try:
                ids_string = ",".join(video_ids)
                url_stats = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={ids_string}&key={YOUTUBE_API_KEY}"
                stats_res = requests.get(url_stats).json()
                for stat_item in stats_res.get('items', []):
                    for rv in recent_videos:
                        if rv['videoId'] == stat_item['id']:
                            rv['views'] = stat_item['statistics'].get('viewCount', '0')
                            rv['likes'] = stat_item['statistics'].get('likeCount', '0')
            except:
                pass # Ignora erro e entrega com "0" em vez de quebrar a tela

        return {
            "subscribers": stats.get('subscriberCount', '0'),
            "views": stats.get('viewCount', '0'),
            "videoCount": stats.get('videoCount', '0'),
            "thumbnail": snippet['thumbnails']['medium']['url'],
            "handle": snippet.get('customUrl', ''),
            "url": f"https://youtube.com/{snippet.get('customUrl', '')}",
            "recentVideos": recent_videos
        }
    except Exception as e:
        print(f"Erro YouTube: {e}")
        return {}

@app.route('/api/stats')
def get_stats():
    global app_cache
    if app_cache["data"] and (time.time() - app_cache["last_updated"]) < CACHE_DURATION:
        return jsonify(app_cache["data"])

    result = {}
    for key, info in BRANDS.items():
        yt = get_youtube_data(info["yt_id"])
        tk = get_tiktok_data(info["tk_username"])
        result[key] = {"youtube": yt, "tiktok": tk}

    app_cache["data"] = result
    app_cache["last_updated"] = time.time()
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5000, debug=True)