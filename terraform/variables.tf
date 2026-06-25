variable "runpod_api_key" {
  type        = string
  description = "RunPod API Key (or set RUNPOD_API_KEY env var)"
  sensitive   = true
}

variable "gpu_type" {
  type        = string
  description = "GPU type for vLLM inference node"
  default     = "NVIDIA GeForce RTX 4090"
}

variable "gpu_count" {
  type        = number
  description = "Number of GPUs to allocate"
  default     = 1
}

variable "cloud_type" {
  type        = string
  description = "RunPod cloud type: SECURE or COMMUNITY"
  default     = "COMMUNITY"
}

variable "volume_size" {
  type        = number
  description = "Size of persistent volume (GB) for model weight caching"
  default     = 50
}

variable "container_disk_size" {
  type        = number
  description = "Ephemeral container disk space (GB)"
  default     = 30
}

variable "llm_model_name" {
  type        = string
  description = "HuggingFace path of LLM model to run in vLLM"
  default     = "Qwen/Qwen2.5-3B-Instruct"
}

variable "huggingface_token" {
  type        = string
  description = "HF Token for gated models (optional)"
  default     = ""
  sensitive   = true
}

variable "data_center_id" {
  type        = string
  description = "RunPod data center ID (must be the same for network volume and pod, e.g. US-CA-2)"
  default     = "US-CA-2"
}
