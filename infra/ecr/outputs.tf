# infra/ecr/outputs.tf
output "backend_repository_url" {
  description = "URL del repositorio ECR del backend"
  value       = aws_ecr_repository.repos["passforge-backend"].repository_url
}

output "frontend_repository_url" {
  description = "URL del repositorio ECR del frontend"
  value       = aws_ecr_repository.repos["passforge-frontend"].repository_url
}

output "registry" {
  description = "Registro ECR (para docker login)"
  value       = split("/", aws_ecr_repository.repos["passforge-backend"].repository_url)[0]
}