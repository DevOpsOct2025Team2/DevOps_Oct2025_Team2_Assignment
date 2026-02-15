# DevOps_Oct2025_Team2_Assignment

A containerized Flask backend with role-based access control, user/file management, and audit logging. Deployed on Google Cloud Run.

## Deployed Backend

- https://devops-oct2025-backend-staging-607806148023.us-central1.run.app/login

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
```

## CI/CD Pipeline (GitHub Actions)

### Setup

1. Add these repository secrets in GitHub:
   - `GCP_SA_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `JWT_SECRET_KEY`
   - `TEST_USERNAME`
   - `TEST_PASSWORD`
2. (Optional) Add notification secrets:
   - `DISCORD_WEBHOOK_PIPELINE`
   - `DISCORD_WEBHOOK_DEV`
   - `DISCORD_WEBHOOK_SECURITY`
3. Ensure the GCP service account in `GCP_SA_KEY` has permission to deploy to Cloud Run and push to Artifact Registry.

### Execute

1. Push to `staging` to run CI and deploy staging.
2. Push to `main` to run CI and deploy production.
3. Monitor runs in `GitHub > Actions > CI Pipeline`.
