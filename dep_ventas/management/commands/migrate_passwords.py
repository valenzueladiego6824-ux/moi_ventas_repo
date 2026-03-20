from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from dep_ventas.models import Usuario

class Command(BaseCommand):
    help = 'Migra contraseñas existentes a formato hasheado'
    
    def handle(self, *args, **options):
        usuarios = Usuario.objects.all()
        migrados = 0
        ya_hasheados = 0
        
        for usuario in usuarios:
            # Verificar si la contraseña NO está hasheada (texto plano)
            if not usuario.password_hash.startswith('pbkdf2_sha256$'):
                try:
                    # Guardar la contraseña actual
                    password_actual = usuario.password_hash
                    # Usar el método set_password que ya tienes en tu modelo
                    usuario.set_password(password_actual)
                    usuario.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Contraseña migrada para: {usuario.nombre_usuario}')
                    )
                    migrados += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error con {usuario.nombre_usuario}: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'→ Ya hasheada: {usuario.nombre_usuario}')
                )
                ya_hasheados += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 Migración completada! {migrados} migrados, {ya_hasheados} ya hasheados')
        )