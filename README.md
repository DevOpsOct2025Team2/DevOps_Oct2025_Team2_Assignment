# DevOps_Oct2025_Team2_Assignment

## Project Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Configuration**:
    Copy `.env.example` to `.env` and fill in your Supabase credentials.
    ```bash
    cp .env.example .env
    ```
    Update the following in `.env`:
    - `SUPABASE_URL`: Your Supabase Project URL
    - `SUPABASE_ANON_KEY`: Your Supabase Anon Key
    - `SUPABASE_SERVICE_KEY`: Your Supabase Service Role Key (for Admin operations)
    - `JWT_SECRET_KEY`: A secure secret key for JWT (or use Supabase JWT verification)

## Running the Application

Start the Flask development server:
```bash
python app.py
```
The app will run at `http://localhost:5000`.

### Admin Dashboard
Access the Admin Dashboard at:
`http://localhost:5000/admin`

## Running Tests

Run the unit and security tests using `pytest`:
```bash
python -m pytest tests/
```