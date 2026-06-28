# Distributed Production Deployment Guide (Vercel + Supabase + RunPod)

This guide describes how to configure, deploy, and run the RAG QA system in a distributed environment:
1. **Vercel**: Hosts the Next.js frontend and the lightweight FastAPI backend API server.
2. **Supabase**: Hosts the PostgreSQL relational database.
3. **RunPod**: Hosts the GPU/CPU-intensive services: vLLM, Celery worker, Redis broker, and Milvus standalone.

---

## 1. Database Provisioning on Supabase

Supabase provides a managed PostgreSQL database. We will use it to store users, chat sessions, message histories, and document metadata.

### Step 1.1: Create a Supabase Project
1. Sign up/log in at [supabase.com](https://supabase.com).
2. Create a new project and select a database password.
3. Once the database is provisioned, go to **Project Settings** -> **Database**.
4. Locate the **Connection string** section. Select the **URI** tab, and copy the connection string.
   * Select **Transaction** mode (usually port `6543`) which is recommended for serverless connections (e.g., Vercel Functions).
   * Replace the password placeholder with your database password, and change the prefix from `postgresql://` to `postgresql+asyncpg://` for Python async compatibility:
     ```env
     # Example connection string:
     postgresql+asyncpg://postgres.your-project-id:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
     ```

### Step 1.2: Run Database Migrations
Run the Alembic migrations from your local workspace to automatically build the tables on Supabase:
```powershell
# Navigate to backend folder
cd backend

# Set the DATABASE_URL environment variable pointing to your Supabase connection string
$env:DATABASE_URL="postgresql+asyncpg://postgres.your-project-id:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true"

# Run Alembic upgrade command
..\.venv\Scripts\python.exe -m alembic upgrade head
```
Verify on your Supabase Dashboard's **Table Editor** that the tables `users`, `sessions`, `messages`, and `documents` have been successfully created.

---

## 2. Deploy Heavy Processing Stack on RunPod

Your RunPod GPU/CPU server will run the vector database (Milvus), message broker (Redis), LLM generator (vLLM), and background task worker (Celery).

### Step 2.1: Open Required Ports on RunPod
When creating your RunPod template or pod, ensure you expose the following ports publicly (or configure secure access/proxies):
* `8000` (vLLM HTTP server)
* `6379` (Redis broker)
* `19530` (Milvus standalone vector DB)

### Step 2.2: Deploy Docker Stack on RunPod
To easily coordinate Redis, Milvus, the Celery worker, and vLLM, you can use the workspace's [docker-compose.yml](file:///c:/Users/debar/newproj/docker-compose.yml) on your RunPod pod:
1. Transfer the project files to your RunPod workspace.
2. In `docker-compose.yml`, you can disable/comment out the `backend`, `frontend`, `postgres`, and `nginx` services since they are hosted on Vercel/Supabase.
3. Configure the environment variables for `celery-worker` in the compose file or `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres.your-project-id:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   MILVUS_HOST=localhost
   VLLM_BASE_URL=http://localhost:8000/v1
   SECRET_KEY=your-secure-jwt-key
   ```
4. Start the stack on RunPod:
   ```bash
   docker compose up -d
   ```
   *Note: Because we modified the `Dockerfile`, the Celery worker container is automatically built using `requirements-worker.txt`, loading `torch`, `sentence-transformers`, and `pdfplumber` to process files and generate embeddings.*

---

## 3. Deploy Backend API Server to Vercel

Vercel will host the FastAPI backend as an on-demand serverless function.

1. Install the Vercel CLI (`npm install -g vercel`) or link your GitHub repository to Vercel.
2. Create a new Vercel project pointing to the **`backend/`** directory.
3. Add the following **Environment Variables** in the Vercel project settings:
   * `VERCEL` = `true` (Tells FastAPI to delegate query embeddings to Celery on RunPod and bypass persistent background loops)
   * `DATABASE_URL` = `postgresql+asyncpg://...` (Your Supabase transaction connection string)
   * `SECRET_KEY` = `your-secure-jwt-key` (Must match the worker's secret key)
   * `CELERY_BROKER_URL` = `redis://<your-runpod-public-ip>:<redis-port>/0` (Broker URL pointing to RunPod Redis)
   * `CELERY_RESULT_BACKEND` = `redis://<your-runpod-public-ip>:<redis-port>/0`
   * `MILVUS_HOST` = `<your-runpod-public-ip>` (IP of RunPod hosting Milvus)
   * `MILVUS_PORT` = `19530`
   * `VLLM_BASE_URL` = `http://<your-runpod-public-ip>:<vllm-port>/v1` (or your RunPod vLLM proxy URL)
   * `MOCK_VLLM` = `false`
4. Deploy the project. Vercel will automatically build the FastAPI serverless API using the optimized, lightweight [requirements.txt](file:///c:/Users/debar/newproj/backend/requirements.txt) (without PyTorch/transformers packages), keeping cold start times low and within Vercel's size limits.
5. Copy your deployed Vercel backend URL (e.g. `https://rag-backend-xyz.vercel.app`).

---

## 4. Deploy Frontend Next.js to Vercel

1. Create a new Vercel project pointing to the **`frontend/`** directory of your repository.
2. Add the following **Environment Variable** in the Vercel project settings:
   * `NEXT_PUBLIC_API_URL` = `https://rag-backend-xyz.vercel.app` (The URL of your deployed Vercel backend)
3. Deploy the project.
4. Once deployed, open the frontend deployment URL in your browser and verify you can Register, Login, Upload documents, and Chat.
