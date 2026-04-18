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
TIKWMAPI_KEY = os.getenv("RAPIDAPI_KEY")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

# Dicionário de Marcas: Configuração central dos IDs
BRANDS = {
    "alpha_dominus": {
        "yt_id": "UCvvcvvdlLiCS6zKs_RUSVtw",
        "tk_username": "alphadominus.tv",
        "fb_page_id": "997796546742674", # Ex: "123456789012345"
        "ig_user_id": "17841480286065294"  # Ex: "17841412345678901"
    },
    "frequencia_mental": {
        "yt_id": "UCT9w5tFL3UxrCVDkTUHF_jQ",
        "tk_username": "afrequenciamental",
        "fb_page_id": None,
        "ig_user_id": None
    }
}

app_cache = {"data": None, "last_updated": 0}
CACHE_DURATION = 3600 # 1 hora de cache para não esgotar as cotas das APIs

def get_tiktok_data(username):
    if not TIKWMAPI_KEY or not username: 
        return {"followers": "0", "likes": "0", "videoCount": "0", "recentVideos": []}
    
    profile_data = {
        "followers": "0", 
        "likes": "0", 
        "videoCount": "0", 
        "recentVideos": [],
        "handle": f"@{username}",
        "url": f"https://www.tiktok.com/@{username}"
    }
    
    headers = {"x-tikwmapi-key": TIKWMAPI_KEY}
    
    try:
        url_profile = "https://api.tikwmapi.com/user/info"
        res_profile = requests.get(url_profile, headers=headers, params={"unique_id": username})
        data_profile = res_profile.json()
        stats = data_profile.get('data', {}).get('stats', {})
        profile_data["followers"] = str(stats.get('followerCount', '0'))
        profile_data["likes"] = str(stats.get('heartCount', '0'))
        profile_data["videoCount"] = str(stats.get('videoCount', '0'))
    except Exception as e:
        print(f"Erro perfil TK {username}: {e}")

    try:
        url_videos = "https://api.tikwmapi.com/user/posts"
        res_videos = requests.get(url_videos, headers=headers, params={"unique_id": username, "count": 10, "cursor": 0})
        data_videos = res_videos.json()
        videos_list = data_videos.get('data', {}).get('videos', [])
        
        recent_videos = []
        for v in videos_list[:3]:
            recent_videos.append({
                "title": v.get('title', ''),
                "thumbnail": v.get('cover', ''),
                "videoId": v.get('video_id', ''),
                "views": str(v.get('play_count', '0')),
                "likes": str(v.get('digg_count', '0')),
                "comments": str(v.get('comment_count', '0')),
                "url": f"https://www.tiktok.com/@{username}/video/{v.get('video_id')}"
            })
        profile_data["recentVideos"] = recent_videos
    except Exception as e:
        print(f"Erro vídeos TK {username}: {e}")

    return profile_data

def get_youtube_data(channel_id):
    if not YOUTUBE_API_KEY or not channel_id: return {}
    try:
        url_ch = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet,contentDetails&id={channel_id}&key={YOUTUBE_API_KEY}"
        data = requests.get(url_ch).json()
        if 'items' not in data: return {} 
        
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
                "views": "0", "likes": "0", "comments": "0",
                "url": f"https://youtube.com/watch?v={vid_id}"
            })
            
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
                            rv['comments'] = stat_item['statistics'].get('commentCount', '0')
            except:
                pass

        return {
            "subscribers": stats.get('subscriberCount', '0'),
            "views": stats.get('viewCount', '0'),
            "videoCount": stats.get('videoCount', '0'),
            "handle": snippet.get('customUrl', ''),
            "url": f"https://youtube.com/{snippet.get('customUrl', '')}",
            "recentVideos": recent_videos
        }
    except Exception as e:
        print(f"Erro YouTube: {e}")
        return {}

def get_meta_data(fb_page_id, ig_user_id):
    """Busca métricas do Instagram e Facebook através da Graph API"""
    if not META_ACCESS_TOKEN or not fb_page_id or not ig_user_id:
        return {"instagram": {}, "facebook": {}}

    meta_data = {
        "instagram": {"followers": "0", "likes": "0", "videoCount": "0", "recentVideos": []},
        "facebook": {"followers": "0", "likes": "0", "videoCount": "0", "recentVideos": []}
    }

    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}

    # 1. Instagram
    try:
        url_ig = f"https://graph.facebook.com/v19.0/{ig_user_id}?fields=username,followers_count,media_count,media.limit(3){{caption,media_url,thumbnail_url,permalink,like_count,comments_count}}"
        res_ig = requests.get(url_ig, headers=headers).json()
        
        meta_data["instagram"]["followers"] = str(res_ig.get("followers_count", "0"))
        meta_data["instagram"]["videoCount"] = str(res_ig.get("media_count", "0"))
        meta_data["instagram"]["handle"] = f"@{res_ig.get('username', '')}"
        meta_data["instagram"]["url"] = f"https://instagram.com/{res_ig.get('username', '')}"

        total_recent_likes = 0
        recent_ig_videos = []
        for item in res_ig.get("media", {}).get("data", []):
            likes = item.get("like_count", 0)
            total_recent_likes += likes
            recent_ig_videos.append({
                "title": item.get("caption", "")[:50] + "...",
                "thumbnail": item.get("thumbnail_url") or item.get("media_url", ""),
                "videoId": item.get("id", ""),
                "views": "0",
                "likes": str(likes),
                "comments": str(item.get("comments_count", "0")),
                "url": item.get("permalink", "")
            })
            
        meta_data["instagram"]["likes"] = str(total_recent_likes)
        meta_data["instagram"]["recentVideos"] = recent_ig_videos
    except Exception as e:
        print(f"Erro no Instagram: {e}")

    # 2. Facebook (PERFIL ISOLADO DOS POSTS)
    try:
        # Primeiro pega só os seguidores e likes (Isso não falha)
        url_fb_profile = f"https://graph.facebook.com/v19.0/{fb_page_id}?fields=name,followers_count,fan_count"
        res_fb_profile = requests.get(url_fb_profile, headers=headers).json()
        
        meta_data["facebook"]["followers"] = str(res_fb_profile.get("followers_count", "0"))
        meta_data["facebook"]["likes"] = str(res_fb_profile.get("fan_count", "0"))
        meta_data["facebook"]["handle"] = res_fb_profile.get("name", "")
        meta_data["facebook"]["url"] = f"https://facebook.com/{fb_page_id}"
        meta_data["facebook"]["videoCount"] = "0" # Removido o N/D
    except Exception as e:
        print(f"Erro no Perfil do Facebook: {e}")

    try:
        # Depois tenta pegar os posts separadamente
        url_fb_posts = f"https://graph.facebook.com/v19.0/{fb_page_id}/posts?limit=3&fields=message,full_picture,permalink_url,likes.summary(true),comments.summary(true)"
        res_fb_posts = requests.get(url_fb_posts, headers=headers).json()
        
        recent_fb_posts = []
        for post in res_fb_posts.get("data", []):
            likes_count = post.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments_count = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            recent_fb_posts.append({
                "title": post.get("message", "")[:50] + "..." if post.get("message") else "Publicação do Facebook",
                "thumbnail": post.get("full_picture", "https://via.placeholder.com/300x200?text=Facebook"),
                "videoId": post.get("id", ""),
                "views": "0", 
                "likes": str(likes_count),
                "comments": str(comments_count),
                "url": post.get("permalink_url", f"https://facebook.com/{post.get('id')}")
            })
            
        meta_data["facebook"]["recentVideos"] = recent_fb_posts
    except Exception as e:
        print(f"Erro nos Posts do Facebook: {e}")

    return meta_data
    """Busca métricas do Instagram e Facebook através da Graph API"""
    if not META_ACCESS_TOKEN or not fb_page_id or not ig_user_id:
        return {"instagram": {}, "facebook": {}}

    meta_data = {
        "instagram": {"followers": "0", "likes": "0", "videoCount": "0", "recentVideos": []},
        "facebook": {"followers": "0", "likes": "0", "videoCount": "0", "recentVideos": []}
    }

    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}

    # 1. Instagram
    try:
        url_ig = f"https://graph.facebook.com/v19.0/{ig_user_id}?fields=username,followers_count,media_count,media.limit(3){{caption,media_url,thumbnail_url,permalink,like_count,comments_count}}"
        res_ig = requests.get(url_ig, headers=headers).json()
        
        meta_data["instagram"]["followers"] = str(res_ig.get("followers_count", "0"))
        meta_data["instagram"]["videoCount"] = str(res_ig.get("media_count", "0"))
        meta_data["instagram"]["handle"] = f"@{res_ig.get('username', '')}"
        meta_data["instagram"]["url"] = f"https://instagram.com/{res_ig.get('username', '')}"

        total_recent_likes = 0
        media_list = res_ig.get("media", {}).get("data", [])
        
        recent_ig_videos = []
        for item in media_list:
            likes = item.get("like_count", 0)
            total_recent_likes += likes
            
            recent_ig_videos.append({
                "title": item.get("caption", "")[:50] + "...",
                "thumbnail": item.get("thumbnail_url") or item.get("media_url", ""),
                "videoId": item.get("id", ""),
                "views": "0", # Omitido propositalmente devido às limitações da API Graph
                "likes": str(likes),
                "comments": str(item.get("comments_count", "0")),
                "url": item.get("permalink", "")
            })
            
        meta_data["instagram"]["likes"] = str(total_recent_likes)
        meta_data["instagram"]["recentVideos"] = recent_ig_videos

    except Exception as e:
        print(f"Erro no Instagram: {e}")

    # 2. Facebook (CORRIGIDO PARA PUXAR POSTS)
    try:
        # Adicionado published_posts.limit(3) na query
        url_fb = f"https://graph.facebook.com/v19.0/{fb_page_id}?fields=name,followers_count,fan_count,published_posts.limit(3){{message,full_picture,permalink_url,likes.summary(true),comments.summary(true)}}"
        res_fb = requests.get(url_fb, headers=headers).json()
        
        meta_data["facebook"]["followers"] = str(res_fb.get("followers_count", "0"))
        meta_data["facebook"]["likes"] = str(res_fb.get("fan_count", "0"))
        meta_data["facebook"]["handle"] = res_fb.get("name", "")
        meta_data["facebook"]["url"] = f"https://facebook.com/{fb_page_id}"

        recent_fb_posts = []
        posts_data = res_fb.get("published_posts", {}).get("data", [])
        
        for post in posts_data:
            likes_count = post.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments_count = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            
            recent_fb_posts.append({
                "title": post.get("message", "")[:50] + "..." if post.get("message") else "Publicação do Facebook",
                "thumbnail": post.get("full_picture", "https://via.placeholder.com/300x200?text=Facebook"),
                "videoId": post.get("id", ""),
                "views": "0", 
                "likes": str(likes_count),
                "comments": str(comments_count),
                "url": post.get("permalink_url", f"https://facebook.com/{post.get('id')}")
            })
            
        meta_data["facebook"]["recentVideos"] = recent_fb_posts
        meta_data["facebook"]["videoCount"] = "N/D" # O Facebook não devolve um contador simples de publicações totais

    except Exception as e:
        print(f"Erro no Facebook: {e}")

    return meta_data

@app.route('/api/stats')
def get_stats():
    global app_cache
    if app_cache["data"] and (time.time() - app_cache["last_updated"]) < CACHE_DURATION:
        return jsonify(app_cache["data"])

    result = {}
    for key, info in BRANDS.items():
        yt = get_youtube_data(info.get("yt_id"))
        tk = get_tiktok_data(info.get("tk_username"))
        
        # Só tenta procurar os dados da Meta se os IDs estiverem configurados
        fb_id = info.get("fb_page_id")
        ig_id = info.get("ig_user_id")
        meta_dados = get_meta_data(fb_id, ig_id) if (fb_id and ig_id) else {"instagram": {}, "facebook": {}}
        
        result[key] = {
            "youtube": yt, 
            "tiktok": tk,
            "instagram": meta_dados.get("instagram", {}),
            "facebook": meta_dados.get("facebook", {})
        }

    app_cache["data"] = result
    app_cache["last_updated"] = time.time()
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5000, debug=True)