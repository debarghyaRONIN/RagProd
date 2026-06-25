# RunPod GPU Pod running vLLM OpenAI API Server
resource "runpod_pod" "vllm_llm" {
  name                 = "rag-vllm-llm"
  image_name           = "vllm/vllm-openai:v0.6.1"
  gpu_type_ids         = [var.gpu_type]
  gpu_count            = var.gpu_count
  cloud_type           = var.cloud_type
  container_disk_in_gb = var.container_disk_size
  
  # Expose vLLM port
  ports                = ["8000/http"]

  env = {
    # Mount HuggingFace cache onto the container workspace disk
    HF_HOME                = "/workspace/huggingface"
    HUGGING_FACE_HUB_TOKEN = var.huggingface_token
  }

  # Command to launch vLLM with the specified model and hardware configurations
  docker_start_cmd = [
    "--model", var.llm_model_name,
    "--dtype", "bfloat16",
    "--max-model-len", "4096",
    "--gpu-memory-utilization", "0.80",
    "--enable-prefix-caching"
  ]
}
