# infra/ecr/main.tf
# Repositorios de imágenes compartidos por todos los ambientes.
# La misma imagen (tag = SHA del commit) se despliega en staging y en producción.
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project   = "passforge"
      ManagedBy = "Terraform"
    }
  }
}

locals {
  repositories = ["passforge-backend", "passforge-frontend"]
}

resource "aws_ecr_repository" "repos" {
  for_each = toset(local.repositories)

  name = each.value
  # Un tag (SHA) nunca se sobrescribe: lo desplegado es siempre trazable
  image_tag_mutability = "IMMUTABLE"
  # Permite destruir el repo aunque tenga imágenes (útil en AWS Academy)
  force_delete = true

  # Escaneo de vulnerabilidades automático al subir cada imagen
  image_scanning_configuration {
    scan_on_push = true
  }
}

# Conserva solo las últimas 10 imágenes de cada repo (suficiente para rollback)
resource "aws_ecr_lifecycle_policy" "keep_last_10" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Conservar solo las ultimas 10 imagenes"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}