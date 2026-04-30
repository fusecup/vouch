output "server_ip" {
  value = digitalocean_droplet.web.ipv4_address
}

output "private_key_pem" {
  value     = tls_private_key.web.private_key_pem
  sensitive = true
}

output "certificate" {
  value     = cloudflare_origin_ca_certificate.web.certificate
  sensitive = true
}
