"""
URL configuration for configuracion project.
"""
from django.contrib import admin
from django.urls import path
from dep_ventas import views

urlpatterns = [
    # Autenticación
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Páginas principales
    path('inicio/', views.inicio, name='inicio'),
    path('reportes/', views.reportes, name='reportes'),
    path('registrar-articulos/', views.registrar_articulos, name='registrar_articulos'),
    
    # APIs de datos generales
    path('api/consultar-datos/', views.api_consultar_datos, name='api_consultar_datos'),
    path('api/detalles-orden/<str:numero_orden>/', views.api_detalles_orden, name='api_detalles_orden'),
    
    # APIs de catálogos
    path('api/obras/', views.api_obras, name='api_obras'),
    path('api/proveedores/', views.api_proveedores, name='api_proveedores'),
    path('api/estatus/', views.api_estatus, name='api_estatus'),
    path('api/solicitantes/', views.api_solicitantes, name='api_solicitantes'),
    path('api/articulos/', views.api_articulos, name='api_articulos'),
    path('api/unidades/', views.api_unidades, name='api_unidades'),
    
    # APIs de operaciones (DELETE, UPDATE)
    path('api/eliminar-orden/<str:numero_orden>/', views.eliminar_orden, name='eliminar_orden'),
    path('api/actualizar-orden/<str:numero_orden>/', views.actualizar_orden, name='actualizar_orden'),
    
    # APIs de reportes
    path('api/reportes/obra-resumen/', views.reporte_obra_resumen, name='reporte_obra_resumen'),
    path('api/reportes/obra-detalle/', views.reporte_obra_detalle, name='reporte_obra_detalle'),
    path('api/reportes/compras-mensuales/', views.reporte_compras_mensuales, name='reporte_compras_mensuales'),
    path('api/exportar-excel/', views.exportar_reporte_excel, name='exportar_excel'),
    path('api/reporte-busqueda/', views.api_reporte_busqueda, name='api_reporte_busqueda'),


    # Gestion de usuarios
    path('usuarios/', views.gestion_usuarios, name='gestion_usuarios'),
    path('api/usuarios/', views.api_usuarios, name='api_usuarios'),
    path('api/usuarios/crear/', views.api_crear_usuario, name='api_crear_usuario'),
    path('api/usuarios/<int:usuario_id>/', views.api_usuario_detalle, name='api_usuario_detalle'),
    path('api/usuarios/actualizar/<int:usuario_id>/', views.api_actualizar_usuario, name='api_actualizar_usuario'),
    path('api/usuarios/eliminar/<int:usuario_id>/', views.api_eliminar_usuario, name='api_eliminar_usuario'),

]