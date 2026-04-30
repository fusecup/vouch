

# Setting up the providers
provider "digitalocean" {
  token = var.digitalocean_token
}


# Digital Ocean Resources ========================

# Define Droplet
resource "digitalocean_droplet" "web" {
  image      = "ubuntu-20-04-x64"
  name       = "vouch-web"
  region     = "nyc1"
  size       = "s-2vcpu-2gb-amd"
  ssh_keys   = [var.g_ssh_key, var.github_ssh_key]
  monitoring = true
  user_data  = templatefile("${path.module}/userdata.tftpl", {})
  backups    = true
  backup_policy {
    plan = "daily"
    hour = 4
  }
  lifecycle {
    prevent_destroy = false
  }
}

# Define Firewall
resource "digitalocean_firewall" "web" {
  name        = "vouch-tf-web-firewall"
  droplet_ids = [digitalocean_droplet.web.id]
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "icmp"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# Grouping all resources into a project
resource "digitalocean_project" "vouch" {
  name        = "Terraform"
  description = "All the resources that belong to vouch project"
  purpose     = "Web Application"
  environment = "Production"
  resources   = [digitalocean_droplet.web.urn]
}




