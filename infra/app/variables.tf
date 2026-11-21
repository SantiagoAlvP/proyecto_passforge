# infra/app/variables.tf
variable "aws_region" {
  description = "Región de AWS donde se desplegarán los recursos"
  type        = string
  default     = "us-east-1"
}

variable "environment_name" {
  description = "Nombre del ambiente (staging o production)"
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.environment_name)
    error_message = "environment_name debe ser \"staging\" o \"production\"."
  }
}

variable "backend_image_uri" {
  description = "URI completa de la imagen del backend en ECR (repo:tag)"
  type        = string
}

variable "frontend_image_uri" {
  description = "URI completa de la imagen del frontend en ECR (repo:tag)"
  type        = string
}

variable "app_version" {
  description = "Versión desplegada (en el pipeline es el SHA del commit)"
  type        = string
  default     = "manual"
}
# --- Autoescalado del backend (modificación 3) ---

variable "enable_autoscaling" {
  description = "Activa el autoescalado del servicio backend en ECS"
  type        = bool
  default     = true
}

variable "backend_min_tasks" {
  description = "Mínimo de tareas del backend"
  type        = number
  default     = 1
}

variable "backend_max_tasks" {
  description = "Máximo de tareas del backend (controla el costo en el Learner Lab)"
  type        = number
  default     = 3

  validation {
    condition     = var.backend_max_tasks >= var.backend_min_tasks && var.backend_max_tasks <= 5
    error_message = "backend_max_tasks debe ser >= backend_min_tasks y <= 5."
  }
}

variable "backend_cpu_target" {
  description = "CPU promedio objetivo (%) del servicio backend"
  type        = number
  default     = 60
}

variable "backend_requests_per_task_target" {
  description = "Peticiones por tarea por minuto (ALB) que se buscan mantener"
  type        = number
  default     = 3000
}
