# Utilise une image Python légère
FROM python:3.12-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier des dépendances et les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le reste du code de l'application
COPY . .

# Port HTTP ARGOS
EXPOSE 5002

# Serveur WSGI de production; les migrations sont executees separement.
CMD ["sh", "-c", "python -m app.bootstrap && exec gunicorn --bind 0.0.0.0:5002 --workers 3 --timeout 60 wsgi:app"]
