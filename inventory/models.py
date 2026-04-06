from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save


class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
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


class Atencion(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE,
        related_name='atenciones'
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
        return f'Atencion de {self.cliente} el {self.fecha.strftime('%d/%m/%Y %H:%M')}'

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
        cliente_str = str(self.cliente) if self.cliente else 'Sin cliente'
        return f'Venta #{self.pk} - {cliente_str} - ${self.total}'

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

    
class Reserva(models.Model):

    ESTADOS_RESERVA = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='reservas') 
    servicios = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='reservas', null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_RESERVA, default='pendiente')
    fecha_turno = models.DateTimeField()
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-fecha_turno']

    def __str__(self):
        return f'Reserva #{self.pk} - {self.cliente} - {self.fecha_turno.strftime('%d/%m/%Y %H:%M')}'


@receiver(post_save, sender=Reserva)
def reserva_a_atencion(sender, instance, **kwargs):
    if instance.estado == 'completada':
        existe = Atencion.objects.filter(
            cliente = instance.cliente,
            fecha = instance.fecha_turno,
        ).exists()

        if not existe:
            atencion = Atencion.objects.create(
                cliente = instance.cliente,
                fecha = instance.fecha_turno,
                notas = instance.descripcion,
            )
            if instance.servicios:
                AtencionServicio.objects.create(
                    atencion = atencion,
                    servicio = instance.servicios,
                    precio_aplicado = instance.servicios.precio,
                )
