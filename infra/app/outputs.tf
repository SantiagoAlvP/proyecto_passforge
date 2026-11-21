# infra/app/outputs.tf
output "alb_url" {
  description = "URL pública de la aplicación (ALB)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "backend_service_name" {
  description = "Nombre del servicio ECS del backend"
  value       = aws_ecs_service.backend.name
}

output "frontend_service_name" {
  description = "Nombre del servicio ECS del frontend"
  value       = aws_ecs_service.frontend.name
}