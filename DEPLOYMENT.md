# Distributed Production Deployment Guide (Vercel + Supabase + RunPod)

This guide describes how to configure, deploy, and run the RAG QA system in a distributed environment:
1. **Next.js Frontend**: Deployed on **Vercel** for optimal client-side load performance.
2. **PostgreSQL Relational DB**: Hosted on **Supabase** for a managed, transaction-pooled relational store.
3. **Backend Stack (FastAPI + Celery + Milvus + vLLM)**: Run on **RunPod (GPU + proper CPU)** to eliminate Vercel serverless limitations, cold starts, and package size limits.

---

## 1. Database Provisioning on Supabase

Supabase provides the managed PostgreSQL database used to store users, chat sessions, message histories, and document metadata.

### Step 1.1: Create a Supabase Project
1. Log in to [supabase.com](https://supabase.com).
2. Create a new project.
3. Go to **Project Settings** -> **Database**.
4. In the **Connection string** section, copy the connection URI:
   * **DATABASE_URL** (Transaction mode, port `6543`) is used for the application.
   * **DIRECT_URL** (Session mode, port `5432`) is used for migrations.
   * Replace `[YOUR-PASSWORD]` with your actual password and change the prefix to `postgresql+asyncpg://` for SQLAlchemy async compatibility.

### Step 1.2: Run Database Migrations
Run the Alembic migrations from your local workspace to construct all the SQL tables on Supabase:
```powershell
# Navigate to backend folder
cd backend

# Populate your DATABASE_URL and DIRECT_URL inside backend/.env and run:
..\.venv\Scripts\python.exe -m alembic upgrade head
```
Verify on your Supabase dashboard that tables `users`, `sessions`, `messages`, and `documents` have been created.

---

## 2. Deploy Python Backend Stack on RunPod (Recommended Architecture)

Hosting the FastAPI app, Celery worker, Redis broker, and Milvus Standalone together on RunPod provides:
* **No Cold Starts**: Your API is always warm and responsive.
* **Direct Vector DB Access**: FastAPI communicates directly with Milvus and Redis over localhost/internal Docker network with sub-millisecond latency.
* **Local Embedding Generation**: Search query embedding generation is processed locally on GPU/CPU without delegating over the internet.

### Step 2.1: Open Required Ports on RunPod
Ensure the following ports are exposed publicly in your RunPod configuration:
* `8080` (FastAPI REST API server)
* `8000` (vLLM OpenAI server)

### Step 2.2: Deploy Docker Stack on RunPod
Using the workspace's [docker-compose.yml](file:///c:/Users/debar/newproj/docker-compose.yml):
1. Transfer the project files to your RunPod pod workspace.
2. Configure your `.env` on RunPod:
   ```env
   # PostgreSQL (Supabase Connection)
   DATABASE_URL=postgresql+asyncpg://postgres.uehjdzxjjrcuufbmtkxb:debarghyasaha@aws-1-ap-south-1.pooler.supabase.com:6543/postgres
   
   # LLM & Embeddings (Local RunPod internal network)
   VLLM_BASE_URL=http://localhost:8000/v1
   LLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct
   EMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5
   
   # Celery & Milvus (Local RunPod internal network)
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   
   # Security
   SECRET_KEY=debarghyasaha
   DEBUG=false
   MOCK_VLLM=false
   ```
3. Start the entire backend docker stack (including FastAPI, Celery, Redis, and Milvus):
   ```bash
   docker compose up -d
   ```
   *FastAPI will launch on port `8080`, and the Celery worker will load the full requirements (`requirements-worker.txt`) to process uploads.*

---

## 3. Alternative: Deploy Backend API to Vercel (Serverless Option)

If you prefer to host the FastAPI app on Vercel as a Serverless Function, follow these steps:
1. Link your GitHub repository `debarghyaRONIN/RagProd` to Vercel.
2. Import the project and set the **Root Directory** to `backend`.
3. Configure the environment variables in Vercel:
   * `VERCEL` = `true` (Tells the app to delegate query embeddings to Celery on RunPod to stay under size limits)
   * `DATABASE_URL` = `<your-supabase-connection-string>`
   * `SECRET_KEY` = `<your-jwt-secret-key>`
   * `CELERY_BROKER_URL` = `redis://<your-runpod-public-ip>:6379/0`
   * `MILVUS_HOST` = `<your-runpod-public-ip>`
   * `MILVUS_PORT` = `19530`
   * `VLLM_BASE_URL` = `<your-runpod-vllm-url>`
4. Deploy the project.

---

## 4. Deploy Frontend Next.js to Vercel

1. In your Vercel dashboard, click **Add New -> Project** and select your repository.
2. Configure settings:
   * **Root Directory**: Select the **`frontend`** folder.
   * **Framework Preset**: **`Next.js`**.
   * **Environment Variable**:
     * **Key**: `NEXT_PUBLIC_API_URL`
     * **Value**: Set this to either:
       * Your RunPod public proxy URL for port `8080` (e.g. `https://<pod-id>-8080.proxy.runpod.net`) if using **Section 2**.
       * Your Vercel backend deployment URL (e.g. `https://my-backend.vercel.app`) if using **Section 3**.
3. Click **Deploy**!
