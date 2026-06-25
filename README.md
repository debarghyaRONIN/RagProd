# RAG QA System (RagProd)

RagProd is a developer-grade, production-quality self-hosted **Retrieval-Augmented Generation (RAG) Question-Answering system**. 

It brings together a stateless asynchronous **FastAPI backend** (Python), a high-contrast minimalist **Next.js 15 frontend** (TypeScript), **PostgreSQL** for relational user/session storage, **Milvus Standalone** for vector embeddings, and **vLLM** (serving Qwen2.5-3B-Instruct) for GPU-accelerated streaming text generation.

---

## Repository Structure

```
RagProd/
├── backend/          # Python — FastAPI API Server, ORM layer, and Embeddings
├── frontend/         # TypeScript — Next.js 15 App Router & GSAP Animations
├── terraform/        # HCL — Infrastructure provisioning for RunPod GPU nodes
├── .env.example      # Environment variables configuration template
└── docker-compose.yml # hardened containerized infrastructure orchestration
```

---

## Prerequisites

To run this application locally, you will need:
* **Docker Desktop** (configured with WSL2 back-end on Windows).
* **NVIDIA GPU** (RTX 3060 12GB VRAM or higher recommended) with **NVIDIA Container Toolkit** installed to run local vLLM inference.
* **Node.js** (v18+) & **Python** (v3.11+).

---

## Local Setup Guide

### 1. Configure Environment Variables
Copy the root `.env.example` template to `.env` and configure your credentials:
```bash
cp .env.example .env
```
Ensure you generate a secure random 32-character key for JWT signing (e.g., using `openssl rand -hex 32` or similar).

### 2. Boot the Infrastructure Stack
Start the containerized databases (PostgreSql, Milvus Standalone) and the vLLM server:
```bash
docker compose up -d
```
*Note: The database ports (Postgres `5432`, Milvus `19530`, vLLM `8000`) are securely bound to `127.0.0.1` and are not exposed to the public internet.*

### 3. Launch the Backend Server
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1   # Windows PowerShell
   ```
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Run the FastAPI application:
   ```bash
   python -m uvicorn app.main:app --port 8080
   ```

### 4. Launch the Frontend
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to `http://localhost:3000`.

---

## Cloud Deployment (RunPod Terraform Setup)

If your local environment lacks a compatible NVIDIA GPU, you can run the vLLM inference service in the cloud (RunPod) and connect your local backend to it.

1. Navigate to the `terraform/` directory:
   ```bash
   cd terraform
   ```
2. Export your RunPod API Key:
   ```powershell
   $env:RUNPOD_API_KEY="your-api-key"
   ```
3. Initialize the provider and deploy the node:
   ```bash
   terraform init
   terraform apply
   ```
4. Copy the resulting `runpod_proxy_url` and paste it into your backend `.env` file:
   ```env
   # backend/.env
   VLLM_BASE_URL=https://<your-pod-id>-8000.proxy.runpod.net/v1
   MOCK_VLLM=false
   ```

---

## Security Hardening Audit Resolutions
The following vulnerabilities identified in the audit have been resolved:
* **Credentials Exchanged for Variables**: The default MinIO key/secret pair has been extracted to `.env` variables (`MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`).
* **Port Restricton**: Relational and vector databases are restricted to loopback bindings (`127.0.0.1`).
* **Network Segregation**: The docker orchestration uses custom `internal-net` and `public-net` networks. Database containers cannot talk to the public network, securing internal state.
* **Healthcheck Readiness**: Health check logic has been configured on all services to eliminate race conditions on container startup.
