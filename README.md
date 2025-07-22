# FoodApp - Tinder for Recipes

A modern, full-stack web application for discovering, searching, and saving recipes, powered by AI-driven personalized recommendations and Google OAuth authentication.

---

## 🚀 Features

- **Google OAuth Authentication**: Secure login with Google using NextAuth.js.
- **Swipe to Discover**: Tinder-style swipe interface for recipe discovery (For You Page).
- **Personalized AI Recommendations**: Recipes tailored to your tastes using ML and user feedback.
- **Smart Search**: Find recipes by ingredient, cuisine, or cooking time with fuzzy search (Elasticsearch).
- **Save Favorites**: Bookmark recipes for quick access later.
- **User Feedback System**: Like/dislike recipes to improve future recommendations.
- **User Statistics**: Track your preferences and cooking patterns.
- **Mobile-First UI**: Responsive, dark-mode enabled, and optimized for mobile with smooth animations.
- **Real-time Updates**: Recommendations and saved recipes update instantly as you interact.

---

## 🏗️ Architecture

**Frontend**

- [Next.js 15](https://nextjs.org/) (App Router, React 19, TypeScript)
- [NextAuth.js](https://next-auth.js.org/) for Google OAuth
- [Tailwind CSS](https://tailwindcss.com/) for styling
- Mobile-first, PWA-like experience

**Backend**

- [FastAPI](https://fastapi.tiangolo.com/) (Python 3.8+)
- [MariaDB](https://mariadb.org/) for persistent storage
- [scikit-learn](https://scikit-learn.org/) for ML-based recommendations
- [Elasticsearch](https://www.elastic.co/elasticsearch/) for full-text and fuzzy search
- Dockerized for local and production deployment

**Database**

- Recipes, users, feedback, saved recipes, and recommendations stored in MariaDB
- Initial schema and data via `db_init/init.sql` and `db_init/init_dataset.json`
- ML models and vectorizers stored in `ml_models/`

**DevOps**

- All services orchestrated with Docker Compose
- Hot-reload for both frontend and backend in development

---

## ⚡ Getting Started (Development Quickstart)

### Prerequisites

- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- Node.js 18+ (for frontend dev)
- Python 3.8+ (for backend dev)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd FoodApp
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your Google OAuth and DB credentials
```

**Required variables:**

```
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=your_password
MARIADB_DATABASE=foodapp_db
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
BACKEND_API_URL=http://localhost:8000
```

### 3. Start All Services (Recommended)

```bash
docker-compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- MariaDB: localhost:3306
- Elasticsearch: localhost:9200

### 4. Local Development (Hot Reload)

#### Frontend

```bash
cd frontend
npm install
npm run dev
# Visit http://localhost:3000
```

#### Backend

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Visit http://localhost:8000/docs
```

#### Database

- Schema auto-initialized by Docker Compose on first run.
- To manually re-run schema:

```bash
docker-compose exec mariadb mysql -u root -p foodapp_db < db_init/init.sql
```

---

## 🛠️ Development Workflow

1. **Frontend**: Edit React/TypeScript code in `frontend/app/` and components in `frontend/components/`.
2. **Backend**: Edit FastAPI code in `api/` (models, endpoints, ML logic).
3. **Database**: Update schema in `db_init/init.sql` and data in `db_init/init_dataset.json`.
4. **ML/Recommendation Logic**: Update or retrain models in `ml_models/` and scripts in `db_init/`.
5. **Testing**: Use the FastAPI docs at `/docs` for API testing. Frontend can be tested with browser/devtools.
6. **Hot Reload**: Both frontend and backend support hot reload in dev mode.
7. **Contributions**: Fork, branch, PR. Test thoroughly before submitting.

---

## 🚀 Deployment Guide

### Production Deployment

1. **Set production environment variables** in `.env` (use strong DB password, production Google OAuth, etc.)
2. **Configure Google OAuth** for your production domain in the Google Cloud Console.
3. **Build and run with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.yml up --build -d
   ```
4. **Set up SSL** (e.g., with a reverse proxy like Nginx or Caddy).
5. **Backups**: Configure regular MariaDB backups (see MariaDB docs).
6. **Scaling**: For scaling, deploy containers to a cloud provider or orchestrator (Kubernetes, ECS, etc.).

---

## 📋 Viewing Logs

- **All services:**
  ```bash
  docker-compose logs
  ```
- **Backend API logs:**
  ```bash
  docker-compose logs api
  # or, for more detail, attach to the container:
  docker-compose exec api tail -f /var/log/app.log
  ```
- **Frontend logs:**
  ```bash
  docker-compose logs frontend
  # or, in dev mode:
  cd frontend && npm run dev
  ```
- **Database logs:**
  ```bash
  docker-compose logs mariadb
  ```
- **Elasticsearch logs:**
  ```bash
  docker-compose logs elasticsearch
  ```
- **API documentation:**
  [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧠 How Recommendations Work

- **Content-based filtering**: Recipes are vectorized using TF-IDF (title, ingredients, instructions, description) and one-hot encoding (cuisine).
- **User feedback**: Likes/dislikes are tracked and used to weight recommendations.
- **Cosine similarity**: Finds recipes most similar to those you liked, least similar to those you disliked.
- **Elasticsearch**: Used for fast, fuzzy search by title and ingredients.
- **New users**: Get a diverse set of recommendations on first login.

---

## 📁 Project Structure

```
FoodApp/
├── frontend/      # Next.js frontend (React, TypeScript, Tailwind)
├── api/           # FastAPI backend (Python, ML, DB)
├── db_init/       # DB schema, initial data, ML scripts
├── ml_models/     # Saved ML models/vectorizers
├── docker-compose.yml
└── README.md
```

---

## 🤝 Contributing

- Fork the repo, create a feature branch, make changes, test, and submit a PR.
- Please add tests and update docs as needed.

## 📄 License

MIT License. See LICENSE file.

---

**Built with ❤️ using Next.js, FastAPI, MariaDB, and scikit-learn.**
