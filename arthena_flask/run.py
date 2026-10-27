"""Point d'entrée pour le développement local."""
import os
from app import create_app

app = create_app(os.getenv("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    app.run(debug=True, port=5006)
