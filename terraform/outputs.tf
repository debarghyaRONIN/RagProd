output "vllm_pod_id" {
  value       = runpod_pod.vllm_llm.id
  description = "The ID of the provisioned RunPod vLLM GPU pod"
}

output "backend_pod_id" {
  value       = runpod_pod.backend_stack.id
  description = "The ID of the provisioned RunPod Backend GPU pod"
}

output "backend_proxy_url" {
  value       = "https://${runpod_pod.backend_stack.id}-8080.proxy.runpod.net"
  description = "The FastAPI Backend URL to set in NEXT_PUBLIC_API_URL on Vercel"
}

output "vllm_proxy_url" {
  value       = "https://${runpod_pod.vllm_llm.id}-8000.proxy.runpod.net/v1"
  description = "The OpenAI-compatible vLLM endpoint URL"
}
