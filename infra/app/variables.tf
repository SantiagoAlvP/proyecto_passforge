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