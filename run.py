from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Garantir que as pastas necessárias existem
    os.makedirs('dados', exist_ok=True)
    os.makedirs('modelo', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
