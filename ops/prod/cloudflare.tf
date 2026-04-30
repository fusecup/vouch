# Setting up the providers
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# Cloudflare Resources ===========================

# Define DNS Record
resource "cloudflare_record" "web" {
  zone_id = var.cloudflare_zone_id
  name    = "@"
  content = digitalocean_droplet.web.ipv4_address
  type    = "A"
  proxied = true
  comment = "Automated by Terraform"
}

resource "tls_private_key" "web" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "tls_cert_request" "web" {
  private_key_pem = tls_private_key.web.private_key_pem

  subject {
    common_name  = "fusecup.co"
    organization = "fusecup"
  }
}

resource "cloudflare_origin_ca_certificate" "web" {
  csr                = tls_cert_request.web.cert_request_pem
  hostnames          = ["fusecup.co"]
  request_type       = "origin-rsa"
  requested_validity = 365
}
resource "cloudflare_authenticated_origin_pulls_certificate" "web" {
  zone_id     = var.cloudflare_zone_id
  private_key = tls_private_key.web.private_key_pem
  certificate = cloudflare_origin_ca_certificate.web.certificate
}

resource "cloudflare_authenticated_origin_pulls_settings" "web" {
  zone_id = var.cloudflare_zone_id
  enabled = true
}
