from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)  # ← AGREGAR
    apellido = models.CharField(max_length=100, blank=True, null=True)  # ← AGREGAR
    nombre_usuario = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=128)
    rol = models.CharField(max_length=50, default='Usuario')  # ← AGREGAR
    
    class Meta:
        db_table = 'usuarios'
    
    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)
    
    def __str__(self):
        return self.nombre_usuario