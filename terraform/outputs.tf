output "pod_id" {
  value       = runpod_pod.vllm_llm.id
  description = "The ID of the provisioned RunPod GPU pod"
}

output "pod_ip" {
  value       = runpod_pod.vllm_llm.public_ip
  description = "The public IP address of the GPU pod"
}

output "vllm_connection_details" {
  value = {
    direct_ip_url    = "http://${runpod_pod.vllm_llm.public_ip}:8000/v1"
    runpod_proxy_url = "https://${runpod_pod.vllm_llm.id}-8000.proxy.runpod.net/v1"
  }
  description = "vLLM connection URLs to copy-paste into your backend .env file (VLLM_BASE_URL)"
}
