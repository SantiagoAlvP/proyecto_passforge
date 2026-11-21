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
output "backend_autoscaling" {
  description = "Rango de tareas del backend (autoescalado)"
  value       = var.enable_autoscaling ? "${var.backend_min_tasks}-${var.backend_max_tasks} tareas (CPU ${var.backend_cpu_target}% / ${var.backend_requests_per_task_target} req por tarea por minuto)" : "desactivado"
}
