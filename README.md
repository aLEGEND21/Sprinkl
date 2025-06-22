# FoodApp - AI-Powered Recipe Recommendation System

A full-stack web application that provides personalized recipe recommendations using AI and OAuth authentication.

## 🍽️ Features

- **OAuth Authentication**: Secure Google OAuth login
- **Personalized Recommendations**: AI-powered recipe suggestions based on user preferences
- **User Feedback System**: Like/dislike recipes to improve recommendations
- **Recipe Search**: Search recipes with filters (cuisine, cooking time, etc.)
- **User Statistics**: Track preferences and cooking patterns
- **Modern UI**: Dark mode interface with responsive design
- **Real-time Updates**: Recommendations update automatically with user feedback

## 🏗️ Architecture

### Frontend (Next.js)
- **Next.js 15**: React framework with App Router
- **NextAuth.js**: OAuth authentication with Google
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Modern styling with dark mode
- **Server Actions**: Server-side user management

### Backend (FastAPI)
- **FastAPI**: Modern Python web framework
- **MariaDB**: Relational database
- **scikit-learn**: Machine learning for recommendations
- **Docker**: Containerized deployment

### Database
- **MariaDB**: Stores recipes, users, feedback, and recommendations
- **Persistent Storage**: Docker volumes for data persistence

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.8+ (for local backend development)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd FoodApp
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

Required environment variables:
```env
# Database Configuration
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=your_password
MARIADB_DATABASE=foodapp_db

# Google OAuth (Required for authentication)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Backend API URL
BACKEND_API_URL=http://localhost:3009
```

### 3. Start the Application
```bash
# Start all services with Docker Compose
docker-compose up --build
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:3009
- **API Documentation**: http://localhost:3009/docs
- **Database**: localhost:3306

## 🔧 Development Setup

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Backend Development
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 3009
```

### Database Management
```bash
# Access MariaDB container
docker-compose exec mariadb mysql -u root -p

# Run migrations (if needed)
docker-compose exec mariadb mysql -u root -p foodapp_db < db_init/init.sql
```

## 📚 API Endpoints

### Authentication
- `POST /api/users/login` - Handle user login and profile creation

### User Management
- `GET /users/{user_id}/recommendations` - Get personalized recommendations
- `POST /users/{user_id}/feedback` - Submit recipe feedback
- `GET /users/{user_id}/stats` - Get user statistics
- `POST /users/{user_id}/recommendations/refresh` - Refresh recommendations

### Recipes
- `GET /recipes/{recipe_id}` - Get specific recipe
- `GET /recipes` - Search recipes with filters

### Health Check
- `GET /` - API health status

## 🤖 How Recommendations Work

1. **Content-Based Filtering**: Analyzes recipe ingredients, cuisine, and cooking time
2. **User Preference Learning**: Tracks likes/dislikes to understand preferences
3. **Similarity Calculation**: Uses TF-IDF vectorization and cosine similarity
4. **Multi-Strategy Approach**: Combines content-based and cuisine-based recommendations
5. **Dynamic Updates**: Recommendations update automatically with user feedback
6. **New User Onboarding**: Generates initial recommendations for new users

## 🔐 Authentication Flow

1. User clicks "Log In with Google" on frontend
2. NextAuth.js handles OAuth flow with Google
3. On successful login, server action calls backend API
4. Backend creates/updates user in database
5. Initial recommendations are generated for new users
6. User session is established with NextAuth.js

## 📁 Project Structure

```
FoodApp/
├── frontend/                 # Next.js frontend application
│   ├── app/                 # App Router pages and components
│   ├── public/              # Static assets
│   └── package.json         # Frontend dependencies
├── api/                     # FastAPI backend application
│   ├── main.py             # Main API application
│   ├── database.py         # Database management
│   ├── recommendation_engine.py  # ML recommendation logic
│   └── requirements.txt    # Python dependencies
├── db_init/                # Database initialization
│   ├── init.sql           # Database schema
│   └── init_dataset.csv   # Initial recipe data
├── ml_models/              # Pre-trained ML models
├── docker-compose.yml      # Docker services configuration
└── README.md              # This file
```

## 🛠️ Development Workflow

### Adding New Features
1. **Frontend Changes**: Edit files in `frontend/app/`
2. **Backend Changes**: Edit files in `api/`
3. **Database Changes**: Update `db_init/init.sql` and run migrations
4. **Testing**: Use the API documentation at `/docs` for testing endpoints

### Code Organization
- **Frontend**: React components with TypeScript
- **Backend**: FastAPI with Pydantic models
- **Database**: MariaDB with proper indexing
- **ML**: scikit-learn for recommendation algorithms

## 🚀 Deployment

### Production Deployment
1. Set up production environment variables
2. Configure Google OAuth for production domain
3. Use Docker Compose for production deployment
4. Set up SSL certificates for HTTPS
5. Configure database backups

### Environment Variables for Production
```env
# Production database
MARIADB_PASSWORD=strong_production_password

# Production OAuth
GOOGLE_CLIENT_ID=production_client_id
GOOGLE_CLIENT_SECRET=production_client_secret

# Production API URL
BACKEND_API_URL=https://your-domain.com
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check MariaDB container is running: `docker-compose ps`
   - Verify environment variables in `.env`

2. **OAuth Login Not Working**
   - Verify Google OAuth credentials in `.env`
   - Check authorized redirect URIs in Google Console

3. **Recommendations Not Loading**
   - Check if user exists in database
   - Verify recommendation engine is working
   - Check API logs for errors

4. **Frontend Not Loading**
   - Check if Next.js container is running
   - Verify port 3000 is not in use
   - Check frontend logs

### Logs and Debugging
```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs frontend
docker-compose logs mariadb

# Access API documentation
open http://localhost:3009/docs
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the troubleshooting section
- Open an issue on GitHub

---

**Built with ❤️ using Next.js, FastAPI, and MariaDB**
