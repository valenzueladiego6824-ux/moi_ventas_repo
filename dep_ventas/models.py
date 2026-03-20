from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    nombre_usuario = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=50, default='Usuario')

    class Meta:
        managed = False
        db_table = 'usuarios'

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return self.nombre_usuario


class Proveedores(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre_proveedor = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'proveedores'


class Articulos(models.Model):
    id_articulo = models.AutoField(primary_key=True)
    clave_articulo = models.CharField(max_length=50, null=True, blank=True)
    nombre_articulo = models.CharField(max_length=255)
    unidad = models.CharField(max_length=50, null=True, blank=True)
    id_proveedor = models.ForeignKey(
        Proveedores,
        on_delete=models.RESTRICT,
        db_column='id_proveedor',
        null=True,
        blank=True
    )

    class Meta:
        managed = False
        db_table = 'articulos'


class Obra(models.Model):
    id_obra = models.AutoField(primary_key=True)
    codigo_obra = models.CharField(max_length=50, null=True, blank=True)
    obra = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'obra'


class OrdenCompra(models.Model):
    numero_orden = models.IntegerField(primary_key=True)
    fecha = models.DateField()
    estatus = models.CharField(max_length=50, null=True, blank=True)
    solicitante = models.CharField(max_length=100, null=True, blank=True)
    metodo_pago = models.CharField(max_length=50, null=True, blank=True)
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.RESTRICT,
        db_column='id_usuario',
        null=True,
        blank=True
    )
    id_obra = models.ForeignKey(
        Obra,
        on_delete=models.RESTRICT,
        db_column='id_obra',
        null=True,
        blank=True
    )

    class Meta:
        managed = False
        db_table = 'orden_compra'


class Facturas(models.Model):
    folio_factura = models.CharField(max_length=100)
    numero_orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        db_column='numero_orden'
    )
    fecha_emision = models.DateField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    iva = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'facturas'
        unique_together = (('folio_factura', 'numero_orden'),)


class ArticulosFactura(models.Model):
    folio_factura = models.CharField(max_length=100)
    numero_orden = models.IntegerField()
    id_articulo = models.ForeignKey(
        Articulos,
        on_delete=models.RESTRICT,
        db_column='id_articulo'
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'articulos_factura'
        unique_together = (('folio_factura', 'numero_orden', 'id_articulo'),)


class ArticulosOrdenCompra(models.Model):
    numero_orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        db_column='numero_orden'
    )
    id_articulo = models.ForeignKey(
        Articulos,
        on_delete=models.RESTRICT,
        db_column='id_articulo'
    )
    cantidad = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'articulos_orden_compra'
        unique_together = (('numero_orden', 'id_articulo'),)