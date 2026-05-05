# On utilise une version de Python légère
FROM python:3.9-slim

# On définit le dossier de travail
WORKDIR /app

# ⚠️ NOUVEAU : On installe les outils système requis pour lire les bases de données MySQL
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# On copie le fichier des bibliothèques et on les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On copie tout le reste de ton projet
COPY . .

# On ouvre le port de Hugging Face
EXPOSE 7860

# On lance l'application
CMD ["python", "app.py"]