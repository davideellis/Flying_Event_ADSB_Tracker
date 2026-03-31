locals {
  instance_name = var.project_name
  ssh_key_name  = "${var.project_name}-key"
  public_url    = var.domain_name != "" ? "http://${var.domain_name}" : "http://${aws_lightsail_static_ip.app.ip_address}"
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

  user_data = templatefile("${path.module}/templates/bootstrap.sh.tftpl", {
    repo_url                 = var.repo_url
    repo_branch              = var.repo_branch
    app_secret_key           = var.app_secret_key
    bootstrap_admin_email    = var.bootstrap_admin_email
    bootstrap_admin_password = var.bootstrap_admin_password
    postgres_password        = var.postgres_password
    adsb_provider            = var.adsb_provider
    adsb_poll_seconds        = var.adsb_poll_seconds
    adsb_http_base_url       = var.adsb_http_base_url
    adsb_http_area_path      = var.adsb_http_area_path_template
    public_url               = local.public_url
  })

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
