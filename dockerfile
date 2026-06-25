# Utilise une image Python légère
FROM python:3.10-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Installation des dépendances système (nécessaires pour compiler psycopg2 / PostgreSQL)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie le fichier des dépendances et les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le reste du code de l'application
COPY . .

# Expose le port 5000 pour Flask
EXPOSE 5002

# Commande de lancement
CMD ["flask", "run", "--host=0.0.0.0"]