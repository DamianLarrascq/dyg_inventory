from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.forms import ModelForm
from django.utils.html import format_html
from .models import (Servicio, Cliente, Atencion, AtencionServicio, Producto, Venta, VentaItem, Reserva)
from django import forms


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
        fields = ['cliente', 'servicios', 'fecha_turno', 'estado', 'descripcion']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicios'].queryset = Servicio.objects.filter(activo=True)


@admin.register(Reserva)
class ReservaAdmin(ModelAdmin):
    form = ReservaForm
    list_display = ("cliente", "fecha_turno", "estado", "descripcion")
    list_filter = ("fecha_turno", "estado")
    search_fields = ("cliente__nombre",)
    date_hierarchy = "fecha_turno"
    autocomplete_fields = ("cliente",)
    list_editable = ("estado",)

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(estado='completada')


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
    fields = ('fecha', 'total', 'notas')
    readonly_fields = ('fecha', 'total', 'notas')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Atencion'
    verbose_name_plural = 'Historial de Atenciones'


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
    search_fields = ("nombre", "telefono", "email")
    list_filter = ("created_at",)
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
    list_display = ("cliente", "fecha", "total", "notas_cortas")
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

    @admin.display(description="Notas")
    def notas_cortas(self, obj):
        if obj.notas:
            return obj.notas[:60] + ("…" if len(obj.notas) > 60 else "")
        return "—"


@admin.register(Producto)
class ProductoAdmin(ModelAdmin):
    list_display = ("nombre", "precio_costo", "precio_venta", "stock_display", "activo")
    list_filter = ("activo",)
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
    list_display = ("id", "cliente", "fecha", "total")
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