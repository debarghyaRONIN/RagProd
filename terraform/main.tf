# RunPod Persistent Storage Volume for Model Weight Caching
resource "runpod_network_volume" "hf_cache" {
  name           = "rag-hf-cache-volume"
  size           = var.volume_size
  data_center_id = var.data_center_id
}

# RunPod GPU Pod running vLLM OpenAI API Server
resource "runpod_pod" "vllm_llm" {
  name                 = "rag-vllm-llm"
  image_name           = "vllm/vllm-openai:latest"
  gpu_type_ids         = [var.gpu_type]
  gpu_count            = var.gpu_count
  cloud_type           = var.cloud_type
  container_disk_in_gb = var.container_disk_size
  data_center_ids      = [var.data_center_id]
  
  # Attach persistent storage
  network_volume_id    = runpod_network_volume.hf_cache.id
  
  # Expose vLLM port
  ports                = ["8000/http"]

  env = {
    # Mount HuggingFace cache onto the persistent volume (/workspace)
    HF_HOME                = "/workspace/huggingface"
    HUGGING_FACE_HUB_TOKEN = var.huggingface_token
  }

  # Command to launch vLLM with the specified model and hardware configurations
  docker_start_cmd = [
    var.llm_model_name,
    "--dtype", "bfloat16",
    "--max-model-len", "4096",
    "--gpu-memory-utilization", "0.80",
    "--enable-prefix-caching"
  ]
}
