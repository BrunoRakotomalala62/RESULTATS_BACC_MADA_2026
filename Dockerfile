# ─── Base image Python léger ───
FROM python:3.11-slim

# ─── Répertoire de travail ───
WORKDIR /app

# ─── Installation des dépendances ───
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Copie du code source ───
COPY . .

# ─── Port exposé ───
EXPOSE 5000

# ─── Lancement avec Gunicorn (production) ───
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "60", "api.index:app"]
