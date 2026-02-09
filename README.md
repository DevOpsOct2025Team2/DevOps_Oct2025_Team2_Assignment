# DevOps_Oct2025_Team2_Assignment

A containerized Flask backend with role-based access control, user/file management, and audit logging. Deployed via GHCR and GitHub Pages.

## Prerequisites

- Python 3.8+
- Docker & Docker Compose
- Supabase account (free tier available)

## Project Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR-ORG/DevOps_Oct2025_Team2_Assignment.git
   cd DevOps_Oct2025_Team2_Assignment
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   Update `.env` with Supabase credentials:
   - `SUPABASE_URL`: Your Supabase project URL 
   - `SUPABASE_ANON_KEY`: For client-side authentication
   - `SUPABASE_SERVICE_KEY`: For admin operations 
   - `JWT_SECRET_KEY`: For JWT token signing
   - `SUPABASE_STORAGE_BUCKET`: Bucket name for file uploads (default: `user-files`)
     
## Running the Application

**Local development**:
```bash
python app.py
```

**Docker Compose**:
```bash
docker-compose up
```

**Manual Docker**:
```bash
docker build -t devops-flask:latest .
docker run -p 5000:5000 \
  -e SUPABASE_URL=$SUPABASE_URL \
  -e SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY \
  -e JWT_SECRET_KEY=$JWT_SECRET_KEY \
  devops-flask:latest
```

Access at `http://localhost:5000`

**Endpoints**:
- User Dashboard: `/dashboard`
- Admin Dashboard: `/admin`
- Logout: `/logout`

## Testing

```bash
python -m pytest tests/