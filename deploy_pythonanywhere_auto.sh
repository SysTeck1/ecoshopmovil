#!/bin/bash

# Script automático de deploy para PythonAnywhere
# Ejecutar en PythonAnywhere Bash console después de clonar el repositorio

echo "🚀 Iniciando deploy automático para PythonAnywhere..."

# 1. Activar virtual environment
echo "📦 Activando virtual environment..."
workon venv

# 2. Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -r requirements.txt

# 3. Colectar static files
echo "📁 Colectando archivos estáticos..."
python manage.py collectstatic --noinput

# 4. Ejecutar migraciones
echo "🗄️ Ejecutando migraciones..."
python manage.py migrate

# 5. Crear carpetas necesarias si no existen
echo "📂 Creando carpetas necesarias..."
mkdir -p media/productos
mkdir -p media/imagenes
mkdir -p media/temp

# 6. Setear permisos
echo "🔐 Configurando permisos..."
chmod -R 755 staticfiles/
chmod -R 755 media/

# 7. Verificar configuración
echo "🔍 Verificando configuración..."
python manage.py check --deploy

# 8. Mostrar URLs de prueba
echo "🌐 URLs de prueba:"
echo "   Logo: https://barkley5.pythonanywhere.com/static/img/logo/logo.svg"
echo "   Media: https://barkley5.pythonanywhere.com/media/"

echo "✅ Deploy completado exitosamente!"
echo "🔄 Recuerda recargar la web app en PythonAnywhere Web tab"
