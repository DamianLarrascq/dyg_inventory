from django.contrib import admin
from django.db.models import query
from unfold.admin import ModelAdmin, TabularInline
from django.forms import ModelForm
from django.utils.html import format_html
from .models import (Servicio, Cliente, Atencion, AtencionServicio, Producto, Venta, VentaItem, Reserva, Empleado)
from django import forms

@admin.register(Empleado)
class Empleado(ModelAdmin):
    list_display = ('nombre', 'activo')
    search_fields = ('nombre',)
    list_editable = ('activo',)


class EmpleadoForm(ModelForm):
    nombre = forms.CharField(max_length=100)


class ReservaForm(ModelForm):

    fecha_turno = forms.DateTimeField(
        widget= forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%d/%m/%Y %H:%M',
        ),
        input_formats=['%d/%m/%Y %H:%M'],
    )
    class Meta:
        model = Reserva
        fields = ['cliente', 'empleado', 'servicios', 'fecha_turno', 'estado', 'descripcion']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicios'].queryset = Servicio.objects.filter(activo=True)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "servicios":
            kwargs["queryset"] = Servicio.objects.filter(activo=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(Reserva)
class ReservaAdmin(ModelAdmin):
    form = ReservaForm
    list_display = ("cliente", 'servicio_display', 'fecha_display', 'estado_badge')
    list_filter = ("fecha_turno", "estado")
    search_fields = ("cliente__nombre",)
    date_hierarchy = "fecha_turno"
    autocomplete_fields = ("cliente", 'servicios')
    list_per_page = 20
    readonly_fields = ('resumen_servicios',)

    def servicio_display(self, obj):
        return ", ".join(s.nombre for s in obj.servicios.all()) or "-"
    servicio_display.short_description = 'Servicio'

    def resumen_servicios(self, obj):
        if not obj.pk:
            return '-'

        servicios = obj.servicios.all()
        total = sum(s.precio for s in servicios)

        nombres = ', '.join(s.nombre for s in servicios)

        return f'{nombres} | Total: ${total}'

    def fecha_display(self, obj):
        return obj.fecha_turno.strftime('%d/%m %H:%M')
    fecha_display.short_description = 'Turno'

    def estado_badge(self, obj):
        colors = {
            'pendiente': '#f39c12',
            'confirmada': '#27ae60',
            'cancelada': '#e74c3c',
            'completada': '#3498db',
        }
        color = colors.get(obj.estado, '#7f8c8d')

        return format_html(
            '<span style="background:{}; color:white; padding:4px 8px; border-radius:6px;">{}</span>',
            color,
            obj.get_estado_display()           
        )
    estado_badge.short_description = 'Estado'

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(estado='completada')

    @admin.action(description='Confirmar reservas')
    def confirmar_reservas(modeladmin, request, queryset):
        queryset.update(estado='confirmada')

    @admin.action(description='Completar y generar atención')
    def completar_reserva(modeladmin, request, queryset):
        for reserva in queryset:
            if hasattr(reserva, "atencion"):
                continue

            reserva.estado = 'completada'
            reserva.save()

            atencion = Atencion.objects.create(
                cliente=reserva.cliente,
                reserva=reserva,
                fecha=reserva.fecha_turno,
                notas=reserva.descripcion,
            )

            for servicio in reserva.servicios.all():
                AtencionServicio.objects.create(
                    atencion=atencion,
                    servicio=servicio,
                    precio_aplicado=servicio.precio,
                )

    actions = [confirmar_reservas, completar_reserva]

class ReservaInline(TabularInline):
    model = Reserva
    tab = True
    fields = ('fecha_turno', 'estado', 'descripcion', 'servicios')
    readonly_fields = ('fecha_turno', 'estado', 'descripcion')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Reserva'
    verbose_name_plural = 'Historial de reservas'

class AtencionInline(TabularInline):
    model = Atencion
    tab = True
    fields = ('fecha', 'total', 'servicios_display','notas')
    readonly_fields = ('fecha', 'total', 'servicios_display','notas')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Atencion'
    verbose_name_plural = 'Historial de Atenciones'

    def servicios_display(self, obj):
        return ', '.join(s.nombre for s in obj.servicios.all())
    servicios_display.short_description = 'Servicios'


class AtencionServicioInline(TabularInline):
    model = AtencionServicio
    fields = ('servicio',)
    extra = 1

    class Media:
        js = ('admin/js/autocomplete_precio.js',)


class VentaInline(TabularInline):
    model = Venta
    tab = True
    fields = ('fecha', 'total', 'notas')
    readonly_fields = ('fecha', 'total', 'notas')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Compra'
    verbose_name_plural = 'Historial de compras'


class VentaItemInline(TabularInline):
    model = VentaItem
    fields = ('producto', 'cantidad', 'subtotal_display')
    readonly_fields = ('subtotal_display',)
    autocomplete_fields = ('producto',)
    extra = 1
    tab = True

    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        if obj.pk:
            return f'${obj.subtotal:.2f}'
        return '-'


@admin.register(Cliente)
class ClienteAdmin(ModelAdmin):
    list_display = ("nombre", "telefono", "email", "created_at")
    search_fields = ("nombre", "telefono")
    list_filter = ("created_at",)
    ordering = ('-created_at',)
    inlines = [AtencionInline, ReservaInline, VentaInline]
    readonly_fields = ("created_at",)
    fieldsets = (
        (
            "Información",
            {
                "classes": ["tab"],
                "fields": (("nombre",), ("telefono", "email"), "descripcion", "created_at"),
            },
        ),
    )


@admin.register(Servicio)
class ServicioAdmin(ModelAdmin):
    list_display = ("nombre", "precio", "activo")
    list_filter = ("activo", "precio")
    search_fields = ("nombre",)
    list_editable = ("activo",)


class AtencionForm(ModelForm):
    fecha = forms.DateTimeField(
    widget= forms.DateTimeInput(
        attrs={'type': 'datetime-local'},
        format='%d/%m/%Y %H:%M',
    ),
    input_formats=['%d/%m/%Y %H:%M'],
    )
    class Meta:
        model = Atencion
        fields = '__all__'
        
@admin.register(Atencion)
class AtencionAdmin(ModelAdmin):
    form = AtencionForm
    list_display = ("cliente", 'servicios_display', 'fecha_display', 'total',)
    list_filter = ("fecha", "servicios")
    date_hierarchy = "fecha"
    search_fields = ('cliente__nombre',)
    inlines = [AtencionServicioInline]
    readonly_fields = ("total",)
    autocomplete_fields = ("cliente",)
    fieldsets = (
        (None, {
            'fields': ('cliente', 'fecha', 'total'),
        }),
        ("Notas", {
            'fields': ('notas',),
            'classes': ('collapse',),
        }),
    )

    def servicios_display(self, obj):
        return ', '.join(s.nombre for s in obj.servicios.all())
    servicios_display.short_description = 'Servicios'

    def fecha_display(self, obj):
        return obj.fecha.strftime('%d/%m %H:%M')

    @admin.display(description="Notas")
    def notas_cortas(self, obj):
        if obj.notas:
            return obj.notas[:60] + ("…" if len(obj.notas) > 60 else "")
        return "—"


@admin.register(Producto)
class ProductoAdmin(ModelAdmin):
    list_display = ("nombre", "precio_costo", "precio_venta", "stock_display", "activo")
    list_filter = ("activo", 'stock')
    search_fields = ("nombre",)
    list_editable = ("activo",)

    @admin.display(description="Stock", ordering="stock")
    def stock_display(self, obj):
        if obj.stock == 0:
            return format_html(
                '<span style="color:white; background:#e74c3c; '
                'padding:2px 8px; border-radius:4px; font-weight:bold;">SIN STOCK</span>'
            )
        elif obj.stock <= 3:
            return format_html(
                '<span style="color:white; background:#e67e22; '
                'padding:2px 8px; border-radius:4px;">{} unid.</span>',
                obj.stock,
            )
        return format_html("<span>{} unid.</span>", obj.stock)


@admin.register(Venta)
class VentaAdmin(ModelAdmin):
    list_display = ("cliente", "fecha_display", "total")
    list_filter = ("fecha",)
    search_fields = ("cliente__nombre",)
    date_hierarchy = "fecha"
    inlines = [VentaItemInline]
    readonly_fields = ("total", "fecha")
    autocomplete_fields = ("cliente",)
    fieldsets = (
        (None, {
            'fields': ('cliente',)
        }),
        ('Resumen', {
            'classes': ['tab'],
            'fields': ('total', 'fecha', 'notas'),
        })
    )

    def fecha_display(self, obj):
        return obj.fecha.strftime('%d/%m %H:%M')