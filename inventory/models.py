from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import constraints
from django.utils.html import format_html


class Empleado(models.Model):
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    empleados = models.ManyToManyField(Empleado, related_name='servicios')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'

    def __str__(self):
        return f'{self.nombre} (${self.precio})'


class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True, unique=True)
    telefono = models.CharField(max_length=10)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} (stock: {self.stock})'

    
class Reserva(models.Model):

    ESTADOS_RESERVA = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]

    ESTADO_COLORES = {
        'pendiente': '#f39c12',
        'confirmada': '#27ae60',
        'cancelada': '#e74c3c',
        'completada': '#3498db',
    }

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='reservas') 
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservas')
    servicios = models.ManyToManyField(Servicio, related_name='reservas', blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_RESERVA, default='pendiente')
    fecha_turno = models.DateTimeField()
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_turno']
        constraints = [
            models.UniqueConstraint(
                fields=['empleado', 'fecha_turno'],
                name='unique_reserva_empleado_hora'
            )
        ]

    def __str__(self):
        return f'Reserva #{self.pk} - {self.cliente} - {self.fecha_turno.strftime('%d/%m/%Y %H:%M')}'

    def clean(self):
        if not self.empleado or not self.fecha_turno:
            return
        
        conflicto = Reserva.objects.filter(
            empleado = self.empleado,
            fecha_turno = self.fecha_turno,
        ).exclude(pk=self.pk).exists()

        if conflicto:
            raise ValidationError(f'{self.empleado.nombre} ya tiene una reserva en ese horario.')
    
    def estado_badge(self):
        color = self.ESTADO_COLORES.get(self.estado, '#7f8c8d')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 8px; border-radius:6px;">{}</span>',
            color,
            self.get_estado_display()
        )


def crear_atencion_desde_reserva(reserva):
    if hasattr(reserva, "atencion"):
        return

    atencion = Atencion.objects.create(
        cliente=reserva.cliente,
        reserva=reserva,
        empleado=reserva.empleado,
        fecha=reserva.fecha_turno,
        notas=reserva.descripcion,
    )

    for servicio in reserva.servicios.all():
        AtencionServicio.objects.create(
            atencion=atencion,
            servicio=servicio,
            precio_aplicado=servicio.precio,
        )


class Atencion(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='atenciones'
    )
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'atenciones'
    )
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atencion'
    )
    fecha = models.DateTimeField()
    servicios = models.ManyToManyField(
        Servicio, through='AtencionServicio',
        related_name='atenciones'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Atencion'
        verbose_name_plural = 'Atenciones'
        ordering = ['-fecha']

    def __str__(self):
        return f'Atencion de {self.cliente}'

    def calcular_total(self):
        total = sum(
            item.precio_aplicado for item in self.atencionservicio_set.all()
        )
        return total

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not is_new:
            self.total = self.calcular_total()
            Atencion.objects.filter(pk=self.pk).update(total=self.total)


class AtencionServicio(models.Model):
    atencion = models.ForeignKey(Atencion, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)
    precio_aplicado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Servicio de Atencion'
        verbose_name_plural = 'Servicios de Atencion'

    def __str__(self):
        return f'{self.servicio.nombre} - ${self.precio_aplicado}'

    def save(self, *args, **kwargs):
        if not self.precio_aplicado:
            self.precio_aplicado = self.servicio.precio
        
        super().save(*args, **kwargs)
        self.atencion.save()


class Venta(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete = models.SET_NULL,
        null = True,
        blank = True,
        related_name = 'ventas',
    )
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']

    def __str__(self):
        return f'Venta #{self.pk}'

    def calcular_total(self):
        return sum(item.subtotal for item in self.ventaitem_set.all())

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not is_new:
            self.total = self.calcular_total()
            Venta.objects.filter(pk=self.pk).update(total=self.total)


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Item de Venta'
        verbose_name_plural = 'Items de Venta'

    def __str__(self):
        return f'{self.cantidad} {self.producto.nombre} - ${self.subtotal}'

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            if not self.precio_unitario:
                self.precio_unitario = self.producto.precio_venta
            
            self.producto.stock = models.F('stock') - self.cantidad
            self.producto.save()
            self.producto.refresh_from_db()
        super().save(*args, **kwargs)
        self.venta.save()

