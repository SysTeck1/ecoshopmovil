# 🚀 Deploy Automático en PythonAnywhere

## 📋 Configuración Automática

Este proyecto está configurado para **deploy automático** en PythonAnywhere. Solo sigue estos pasos:

### 🔧 Paso 1: Clonar Repositorio

```bash
cd /home/barkley5/
git clone https://github.com/SysTeck1/EcoMovilShop.git SistemaPOS
cd SistemaPOS
```

### 🔧 Paso 2: Ejecutar Script Automático

```bash
chmod +x deploy_pythonanywhere_auto.sh
./deploy_pythonanywhere_auto.sh
```

### 🔧 Paso 3: Configurar Web App

1. **Ve a Web tab** en PythonAnywhere
2. **Crea nueva web app** o edita existente
3. **Configura WSGI**:
   - **Virtualenv**: `/home/barkley5/.virtualenvs/venv`
   - **WSGI file**: Copia contenido de `pythonanywhere_wsgi_fix.py`

### 🔧 Paso 4: Configurar Static/Media Files

En **Web tab → Static files**:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/barkley5/SistemaPOS/staticfiles` |
| `/media/` | `/home/barkley5/SistemaPOS/media` |

### 🔧 Paso 5: Recargar Web App

Haz clic en **"Reload"** en Web tab.

## ✅ Configuración Incluida

### **Settings.py Configurado:**
- ✅ **DEBUG**: `False` por defecto (configurable por environment)
- ✅ **ALLOWED_HOSTS**: Incluye `barkley5.pythonanywhere.com`
- ✅ **Static files**: `/static/` → `staticfiles/`
- ✅ **Media files**: `/media/` → `media/`
- ✅ **Database**: SQLite (compatible con producción)

### **Templates Configurados:**
- ✅ **Logo**: `{% static 'img/logo/logo.svg' %}`
- ✅ **Dashboard logo URL**: Definido en `DashboardTemplateView`
- ✅ **Imágenes productos**: Soporta media files con fallback

### **Archivos Incluidos:**
- ✅ **Logo SVG**: `static/img/logo/logo.svg`
- ✅ **Default product**: `static/img/default-product.png`
- ✅ **WSGI config**: `pythonanywhere_wsgi_fix.py`
- ✅ **Deploy script**: `deploy_pythonanywhere_auto.sh`

## 🔄 Actualizaciones Futuras

Para actualizar el proyecto en PythonAnywhere:

```bash
cd /home/barkley5/SistemaPOS
git pull origin main
./deploy_pythonanywhere_auto.sh
```

## 📱 URLs de Acceso

- **Principal**: `https://barkley5.pythonanywhere.com/`
- **Admin**: `https://barkley5.pythonanywhere.com/admin/`
- **Logo**: `https://barkley5.pythonanywhere.com/static/img/logo/logo.svg`

## 🔍 Verificación

```bash
# Verificar que todo funcione
python manage.py check --deploy
curl -I https://barkley5.pythonanywhere.com/static/img/logo/logo.svg
```

## 🎯 Listo para Producción

El proyecto está **100% configurado** para producción en PythonAnywhere:

- ✅ **Settings optimizados**
- ✅ **Static/Media configurados**
- ✅ **Logo funcionando**
- ✅ **Imágenes de productos soportadas**
- ✅ **Deploy automático**
- ✅ **Documentación completa**

**🎉 Solo clona, ejecuta el script y recarga la web app!**
