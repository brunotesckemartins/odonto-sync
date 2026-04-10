from flask import Flask, render_template
import os

def create_app():
    app = Flask(__name__)
    
    app.config.from_object('config.Config')
    
    os.makedirs(app.config['DADOS_DIR'], exist_ok=True)
    os.makedirs(app.config['MODELO_DIR'], exist_ok=True)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error_code=404,
                             error_message='Página não encontrada',
                             error_description='A página que você está procurando não existe.'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html',
                             error_code=500,
                             error_message='Erro interno do servidor',
                             error_description='Ocorreu um erro inesperado. Por favor, tente novamente.'), 500
    
    from app.routes import agenda, simulacao, reorganizacao, graficos
    
    app.register_blueprint(agenda.bp)
    app.register_blueprint(simulacao.bp)
    app.register_blueprint(reorganizacao.bp)
    app.register_blueprint(graficos.bp)
    
    return app
