locals {
  instance_name = var.project_name
  ssh_key_name  = "${var.project_name}-key"
}

resource "aws_lightsail_key_pair" "this" {
  count      = var.public_key_path != "" ? 1 : 0
  name       = local.ssh_key_name
  public_key = file(var.public_key_path)
}

resource "aws_lightsail_instance" "app" {
  name              = local.instance_name
  availability_zone = var.availability_zone
  blueprint_id      = var.lightsail_blueprint_id
  bundle_id         = var.lightsail_bundle_id
  key_pair_name     = var.public_key_path != "" ? aws_lightsail_key_pair.this[0].name : null

  user_data = <<-EOT
    #!/bin/bash
    set -euxo pipefail
    apt-get update
    apt-get install -y docker.io docker-compose-v2 git
    systemctl enable docker
    systemctl start docker
  EOT

  tags = {
    Project     = var.project_name
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

resource "aws_lightsail_static_ip" "app" {
  name = "${var.project_name}-ip"
}

resource "aws_lightsail_static_ip_attachment" "app" {
  static_ip_name = aws_lightsail_static_ip.app.name
  instance_name  = aws_lightsail_instance.app.name
}

resource "aws_lightsail_instance_public_ports" "app" {
  instance_name = aws_lightsail_instance.app.name

  port_info {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"
  }

  port_info {
    from_port = 80
    to_port   = 80
    protocol  = "tcp"
  }

  port_info {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
  }
}
