import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega a chave de API do arquivo .env
load_dotenv()

app = Flask(__name__)
# Habilita o CORS para todas as rotas (permite o React se conectar)
CORS(app)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# --- PASSO IMPORTANTE ---
# Substitua pelos IDs reais dos seus canais.
# Para achar o ID: Vá na página do canal do YouTube -> Aba "Sobre" -> "Compartilhar canal" -> "Copiar ID do canal"
CHANNELS = {
    "alpha_dominus": "UCvvcvvdlLiCS6zKs_RUSVtw",
    "frequencia_mental": "UCT9w5tFL3UxrCVDkTUHF_jQ"
}

@app.route('/api/youtube-stats', methods=['GET'])
def get_youtube_stats():
    # Segurança: Verifica se a chave foi carregada
    if not YOUTUBE_API_KEY:
        return jsonify({"error": "Chave da API do YouTube não configurada"}), 500

    # Junta os IDs separados por vírgula para fazer uma única requisição ao YouTube
    ids_string = ",".join(CHANNELS.values())
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={ids_string}&key={YOUTUBE_API_KEY}"

    try:
        response = requests.get(url)
        response.raise_for_status() # Lança um erro se a requisição falhar
        data = response.json()

        # Estrutura JSON limpa que será enviada para o seu React
        result = {
            "alphaDominus": {"subscribers": "0", "views": "0", "videoCount": "0"},
            "frequenciaMental": {"subscribers": "0", "views": "0", "videoCount": "0"}
        }

        # Mapeando a resposta bruta do YouTube para o nosso JSON limpo
        for item in data.get('items', []):
            channel_id = item['id']
            stats = item['statistics']
            
            subs = stats.get('subscriberCount', '0')
            views = stats.get('viewCount', '0')
            videos = stats.get('videoCount', '0')

            if channel_id == CHANNELS['alpha_dominus']:
                result["alphaDominus"] = {
                    "subscribers": subs, 
                    "views": views, 
                    "videoCount": videos
                }
            elif channel_id == CHANNELS['frequencia_mental']:
                result["frequenciaMental"] = {
                    "subscribers": subs, 
                    "views": views, 
                    "videoCount": videos
                }

        return jsonify(result)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro de conexão com o YouTube: {str(e)}"}), 500

# Configuração para rodar localmente e no Render
if __name__ == '__main__':
    # O Render injeta dinamicamente a porta através da variável de ambiente PORT. 
    # Se não encontrar (rodando local), usa a 5000.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)