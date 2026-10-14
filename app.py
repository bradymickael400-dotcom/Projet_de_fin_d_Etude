import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5002")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
