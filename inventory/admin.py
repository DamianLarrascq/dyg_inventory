from django.contrib import admin
from django.utils.html import format_html
from .models import (Servicio, Cliente, Atencion, AtencionServicio, Producto, Venta, VentaItem)


admin.site.site_header = 'Peluqueria DYG'
admin.site.site_title = 'Peluqueria DYG'
admin.site.index_title = 'Panel de Control'


class AtencionInline(admin.TabularInline):
    model = Atencion
    fields = ('fecha', 'total', 'notas')
    readonly_fields = ('fecha', 'total', 'notas')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = 'Atencion'
    verbose_name_plural = 'Historial de Atenciones'


class AtencionServicioInline(admin.TabularInline):
    model = AtencionServicio
    fields = ('servicio', 'precio_aplicado')
    extra = 1

    class Media:
        js = ('admin/js/autocomplete_precio.js',)


class VentaItemInline(admin.TabularInline):
    model = VentaItem
    fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal_display')
    readonly_fields = ('subtotal_display',)
    extra = 1

    @admin.display(description='Subtotal')
    def subtotal_display(self, obj):
        if obj.pk:
            return f'${obj.subtotal:.2f}'
        return '-'


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "telefono", "email", "created_at")
    search_fields = ("nombre", "telefono", "email")
    list_filter = ("created_at",)
    inlines = [AtencionInline]
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {
            "fields": (("nombre",), ("telefono", "email"))
        }),
        ("Información adicional", {
            "fields": ("descripcion", "created_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "activo")
    list_filter = ("activo", "precio")
    search_fields = ("nombre",)
    list_editable = ("activo",)


@admin.register(Atencion)
class AtencionAdmin(admin.ModelAdmin):
    list_display = ("cliente", "fecha", "total", "notas_cortas")
    list_filter = ("fecha", "servicios")
    search_fields = ("cliente__nombre", "cliente__apellido")
    date_hierarchy = "fecha"
    inlines = [AtencionServicioInline]
    readonly_fields = ("total",)
    autocomplete_fields = ("cliente",)

    @admin.display(description="Notas")
    def notas_cortas(self, obj):
        if obj.notas:
            return obj.notas[:60] + ("…" if len(obj.notas) > 60 else "")
        return "—"


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
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
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "fecha", "total")
    list_filter = ("fecha",)
    search_fields = ("cliente__nombre", "cliente__apellido")
    date_hierarchy = "fecha"
    inlines = [VentaItemInline]
    readonly_fields = ("total", "fecha")
    autocomplete_fields = ("cliente",)