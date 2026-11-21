# infra/app/autoscaling.tf
#
# Modificación 3 del proyecto final: autoescalado horizontal del backend.
#
# Antes: el servicio del backend corría siempre con 1 tarea (desired_count = 1).
# Si llegaba más carga de la que una tarea soporta, la latencia subía y aparecían
# errores. Ahora ECS ajusta la cantidad de tareas entre un mínimo y un máximo
# según dos métricas (Target Tracking):
#
#   - CPU promedio del servicio            -> objetivo: 60 %
#   - Peticiones por tarea en el ALB/minuto -> objetivo: 3000
#
# Cuando la carga sube, ECS agrega tareas (y el ALB las registra en el Target
# Group); cuando baja, las retira. El servicio ya tiene
# "lifecycle { ignore_changes = [desired_count] }", así que Terraform no
# deshace lo que el autoescalado decida.

resource "aws_appautoscaling_target" "backend" {
  count = var.enable_autoscaling ? 1 : 0

  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.backend_min_tasks
  max_capacity       = var.backend_max_tasks
}

# Escala por CPU: el backend genera contraseñas y calcula su entropía, así que
# la CPU es el recurso que primero se agota con carga real.
resource "aws_appautoscaling_policy" "backend_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-backend-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.backend[0].service_namespace
  resource_id        = aws_appautoscaling_target.backend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.backend[0].scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value       = var.backend_cpu_target
    scale_out_cooldown = 60  # agrega tareas rápido
    scale_in_cooldown  = 180 # las retira con calma para no oscilar

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# Escala por tráfico: peticiones por tarea medidas en el ALB. Reacciona aunque
# las peticiones sean livianas y la CPU todavía no suba.
resource "aws_appautoscaling_policy" "backend_requests" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-backend-requests"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.backend[0].service_namespace
  resource_id        = aws_appautoscaling_target.backend[0].resource_id
  scalable_dimension = aws_appautoscaling_target.backend[0].scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value       = var.backend_requests_per_task_target
    scale_out_cooldown = 60
    scale_in_cooldown  = 180

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.backend.arn_suffix}"
    }
  }
}
