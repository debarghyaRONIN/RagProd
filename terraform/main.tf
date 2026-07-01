# RunPod GPU Pod running vLLM OpenAI API Server
resource "runpod_pod" "vllm_llm" {
  name                 = "rag-vllm-llm"
  image_name           = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
  gpu_type_ids         = [var.gpu_type]
  gpu_count            = var.gpu_count
  cloud_type           = var.cloud_type
  container_disk_in_gb = var.container_disk_size
  
  # Expose vLLM and FastAPI ports
  ports                = ["8000/http", "8080/http"]

  env = {
    # Mount HuggingFace cache onto the container workspace disk
    HF_HOME                = "/workspace/huggingface"
    HUGGING_FACE_HUB_TOKEN = var.huggingface_token
  }

  # Unified startup command to launch Redis, clone the repo, install requirements in venv (including vllm), and run vLLM, Celery, and FastAPI
  docker_start_cmd = [
    "bash", "-c",
    "export DEBIAN_FRONTEND=noninteractive ; apt-get update ; apt-get install -y redis-server git python3-venv ; redis-server --daemonize yes ; git clone -b Test https://github.com/debarghyaRONIN/RagProd.git /workspace/app ; cd /workspace/app/backend ; python3 -m venv --system-site-packages /workspace/venv ; /workspace/venv/bin/pip install --upgrade pip setuptools wheel ; /workspace/venv/bin/pip install -r requirements-worker.txt ; /workspace/venv/bin/pip install milvus-lite vllm==0.4.2 ; cat <<'EOF' > .env\nDATABASE_URL=postgresql+asyncpg://postgres.uehjdzxjjrcuufbmtkxb:debarghyasaha@aws-1-ap-south-1.pooler.supabase.com:6543/postgres\nCELERY_BROKER_URL=redis://localhost:6379/0\nCELERY_RESULT_BACKEND=redis://localhost:6379/0\nMILVUS_HOST=./milvus.db\nMILVUS_PORT=0\nVLLM_BASE_URL=http://localhost:8000/v1\nLLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct\nEMBEDDING_MODEL_NAME=BAAI/bge-small-en-v1.5\nSECRET_KEY=debarghyasaha\nDEBUG=false\nMOCK_VLLM=false\nEOF\n/workspace/venv/bin/python3 -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-3B-Instruct --dtype bfloat16 --max-model-len 4096 --gpu-memory-utilization 0.80 --enable-prefix-caching & \n/workspace/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info -P solo & \n/workspace/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080"
  ]
}
