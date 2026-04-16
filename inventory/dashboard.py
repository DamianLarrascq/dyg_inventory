from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from datetime import timedelta
from .models import Reserva, Venta, Producto, Cliente, Atencion


def dashboard_callback(request, context):
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    reservas_hoy = Reserva.objects.filter(
        fecha_turno__date = hoy
    ).exclude(estado='cancelada').count()

    reservas_semana = Reserva.objects.filter(
        fecha_turno__date__gte = inicio_semana
    ).exclude(estado='cancelada')

    ventas_hoy = sum(v.total for v in Venta.objects.filter(fecha__date=hoy))
    ventas_mes = sum(v.total for v in Venta.objects.filter(fecha__date__gte=inicio_mes))

    atenciones_hoy_qs = Atencion.objects.filter(fecha__date=hoy)
    atenciones_mes_qs = Atencion.objects.filter(fecha__date__gte=inicio_mes)
    ingresos_atenciones_hoy = sum(a.total for a in atenciones_hoy_qs)
    ingresos_atenciones_mes = sum(a.total for a in atenciones_mes_qs)

    stock_bajo = Producto.objects.filter(stock__lte=3, activo=True).order_by('stock')

    clientes_nuevos = Cliente.objects.filter(
        created_at__date__gte = hoy - timedelta(days=7)
    ).order_by('-created_at')[:5]

    atenciones_semana = Atencion.objects.filter(
        fecha__date__gte=inicio_semana
    ).select_related('cliente').order_by('-fecha')

    context.update({
        'kpi': [
            {
                'title': 'Reservas hoy',
                'metric': reservas_hoy,
                'footer': f'Semana: {reservas_semana.count()}',
            },
            {
                'title': 'Ingresos ventas hoy',
                'metric': f'${ventas_hoy:,.2f}',
                'footer': f'Mes: ${ventas_mes:,.2f}',
            },
            {
                'title': 'Ingresos atenciones hoy',
                'metric': f'${ingresos_atenciones_hoy:,.2f}',
                'footer': f'Mes: ${ingresos_atenciones_mes:,.2f}',
            },
            {
                'title': 'Productos con stock bajo',
                'metric': stock_bajo.count(),
                'footer': 'stock ≤ 3 unidades',
            },
            {
                'title': 'Clientes nuevos',
                'metric': clientes_nuevos.count(),
                'footer': 'Ultimos 7 dias',
            },
        ],
        "tabla_stock": {
            "headers": ["Producto", "Stock"],
            "rows": [
                [
                    format_html(
                        '<a href="{}">{}</a>',
                        reverse("admin:inventory_producto_change", args=[p.pk]),
                        p.nombre,
                    ),
                    p.stock,
                ]
                for p in stock_bajo
            ],
        },
        "tabla_reservas": {
            "headers": ["Cliente", "Servicio", "Fecha", "Estado"],
            "rows": [
                [
                    format_html(
                        '<a href="{}">{}</a>',
                        reverse("admin:inventory_cliente_change", args=[r.cliente.pk]),
                        str(r.cliente),
                    ),
                    ", ".join(s.nombre for s in r.servicios.all()) or '-',
                    format_html(
                        '<a href="{}">{}</a>',
                        reverse("admin:inventory_reserva_change", args=[r.pk]),
                        r.fecha_turno.strftime("%d/%m %H:%M"),
                    ),
                    r.get_estado_display(),
                ]
                for r in reservas_semana.select_related('cliente').prefetch_related('servicios').order_by('fecha_turno')
            ],
        },
        "tabla_clientes": {
            "headers": ["Nombre", "Teléfono", "Fecha de alta"],
            "rows": [
                [
                    format_html(
                        '<a href="{}">{}</a>',
                        reverse("admin:inventory_cliente_change", args=[c.pk]),
                        c.nombre,
                    ),
                    c.telefono,
                    c.created_at.strftime("%d/%m/%Y"),
                ]
                for c in clientes_nuevos
            ],
        },
        "tabla_atenciones": {
            "headers": ["Cliente", "Servicios", "Fecha", "Total"],
            "rows": [
                [
                    format_html(
                        '<a href="{}">{}</a>',
                        reverse("admin:inventory_cliente_change", args=[a.cliente.pk]),
                        str(a.cliente),
                    ),
                    ", ".join(str(s) for s in a.servicios.all()),
                    format_html(
                        '<a href="{}">{}</a>',
                        reverse("admin:inventory_atencion_change", args=[a.pk]),
                        a.fecha.strftime("%d/%m %H:%M"),
                    ),
                    f"${a.total:,.2f}",
                ]
                for a in atenciones_semana
            ],
        },
    })
    return context