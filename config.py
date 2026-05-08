import os

def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')

# Diretório base do projeto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configurações do Flask
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-odontoml-2026'
    DEBUG = _env_bool('DEBUG', True)
    
    # Caminhos
    DADOS_DIR = os.path.join(BASE_DIR, 'dados')
    MODELO_DIR = os.path.join(BASE_DIR, 'modelo')
    DATABASE_PATH = os.path.join(DADOS_DIR, 'odontoml.db')
    CSV_PATH = os.path.join(DADOS_DIR, 'agendamentos.csv')
    
    # Modelo
    MODELO_PATH = os.path.join(MODELO_DIR, 'random_forest.pkl')
    ENCODERS_PATH = os.path.join(MODELO_DIR, 'encoders.pkl')
    
    # Configurações de ML
    TEST_SIZE = 0.2
    RANDOM_STATE = 42
    N_ESTIMATORS = 100
    
    # Thresholds de risco
    RISCO_ALTO = 0.6  # >= 60% = Alto risco
    RISCO_MEDIO = 0.3  # 30-60% = Médio risco
    # < 30% = Baixo risco
    
    # Configuração do Gemini AI
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or None
    GEMINI_MODEL = 'gemini-1.5-flash'
    USE_AI_SUGGESTIONS = _env_bool('USE_AI_SUGGESTIONS', True)  # Se True, usa IA para sugestões inteligentes
    
    # Configuração para API de Clima (integração futura)
    # Sugestão: OpenWeatherMap, WeatherAPI ou similar
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY') or None
    WEATHER_API_URL = 'https://api.openweathermap.org/data/2.5/weather'
    USE_WEATHER_API = _env_bool('USE_WEATHER_API', False)  # Ativar quando API estiver configurada
    DEFAULT_CITY = 'São Paulo'  # Cidade padrão para consultas climáticas

    # Bootstrap para ambiente container/local
    BOOTSTRAP_ON_START = _env_bool('BOOTSTRAP_ON_START', False)
    BOOTSTRAP_REFRESH_DATA = _env_bool('BOOTSTRAP_REFRESH_DATA', False)
    
    # Mapeamento de condições climáticas para o modelo
    WEATHER_CONDITION_MAP = {
        'Clear': 'ensolarado',
        'Clouds': 'nublado',
        'Rain': 'chuvoso',
        'Drizzle': 'chuvoso',
        'Thunderstorm': 'tempestade',
        'Snow': 'chuvoso',
        'Mist': 'nublado',
        'Fog': 'nublado'
    }
