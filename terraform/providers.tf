terraform {
  required_version = ">= 1.0"
  required_providers {
    runpod = {
      source  = "decentralized-infrastructure/runpod"
      version = ">= 1.0.1"
    }
  }
}

provider "runpod" {
  api_key = var.runpod_api_key
}
