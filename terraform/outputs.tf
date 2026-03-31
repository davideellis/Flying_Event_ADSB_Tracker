output "instance_name" {
  value       = aws_lightsail_instance.app.name
  description = "Lightsail instance name."
}

output "instance_public_ip" {
  value       = aws_lightsail_static_ip.app.ip_address
  description = "Public IP attached to the Lightsail instance."
}

output "ssh_key_name" {
  value       = try(aws_lightsail_key_pair.this[0].name, null)
  description = "Registered Lightsail key pair name when a public key path is provided."
}
