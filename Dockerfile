# On utilise une version de Python légère
FROM python:3.9-slim

# On définit le dossier de travail
WORKDIR /app

# On copie le fichier des bibliothèques et on les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On copie tout le reste de ton projet
COPY . .

# On ouvre le port de Hugging Face
EXPOSE 7860

# On lance l'application
CMD ["python", "app.py"]