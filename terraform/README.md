# Terraform Notes

Terraform for this project must live inside this directory.

## Initial Intent

Terraform will manage the low-cost AWS infrastructure for v1, expected to include:
- A Lightsail instance
- A static IP
- Network access rules
- Supporting outputs for deployment and DNS wiring

## Layout Guidance

Start simple, but keep room for growth.

Possible initial file layout:
- `providers.tf`
- `main.tf`
- `variables.tf`
- `outputs.tf`

If the infrastructure expands later, add:
- `modules/`
- `environments/`

## Workflow Expectations

- Keep Terraform changes isolated to this directory
- Run `terraform fmt` and `terraform validate` as part of infra changes
- Document required variables and deployment steps here as infra is added

## Current Variables Worth Setting

- `app_secret_key`
- `bootstrap_admin_password`
- `domain_name`

When `domain_name` is set and already points at the Lightsail static IP, the bootstrap script will configure nginx for that hostname and request a Let's Encrypt certificate automatically.
