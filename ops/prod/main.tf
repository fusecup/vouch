# Terraform Cloud Setup
terraform {
  cloud {
    organization = "fusecup"
    workspaces {
      name = "fusecup"
    }
  }
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5"
    }
  }
}
