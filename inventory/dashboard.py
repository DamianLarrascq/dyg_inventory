from django.db.models import Sum
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from datetime import timedelta
from .models import Reserva, Venta, Producto, Cliente, Atencion


def dashboard_callback(request, context):
    hoy = timezone.now().date()
    ayer = hoy - timedelta(days=1)
    inicio_mes = hoy.replace(day=1)
    inicio_semana = hoy - timedelta(days=hoy.weekday())

    reservas_hoy = Reserva.objects.filter(
    fecha_turno__date=hoy).exclude(estado='cancelada').select_related('cliente','empleado').prefetch_related('servicios').order_by('fecha_turno')

    ventas_hoy = sum(v.total for v in Venta.objects.filter(fecha__date=hoy))
    ventas_ayer = sum(v.total for v in Venta.objects.filter(fecha__date=ayer))
    ventas_mes = sum(v.total for v in Venta.objects.filter(fecha__date__gte=inicio_mes))

    atenciones_hoy_qs = Atencion.objects.filter(fecha__date=hoy)
    atenciones_ayer_qs = Atencion.objects.filter(fecha__date=ayer)
    atenciones_mes_qs = Atencion.objects.filter(fecha__date__gte=inicio_mes)

    ingresos_atenciones_hoy = sum(a.total for a in atenciones_hoy_qs)
    ingresos_atenciones_ayer = sum(a.total for a in atenciones_ayer_qs)
    ingresos_atenciones_mes = sum(a.total for a in atenciones_mes_qs)

    ultimos_7_dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
    labels_grafico = [d.strftime('%d/%m') for d in ultimos_7_dias]

    datos_ingresos = []
    for dia in ultimos_7_dias:
        ventas_dia = Venta.objects.filter(fecha__date=dia).aggregate(total=Sum('total'))['total'] or 0
        atenciones_dia = Atencion.objects.filter(fecha__date=dia).aggregate(total=Sum('total'))['total'] or 0
        datos_ingresos.append(float(ventas_dia + atenciones_dia))

    stock_bajo = Producto.objects.filter(stock__lte=3, activo=True).order_by('stock')

    clientes_nuevos = Cliente.objects.filter(
        created_at__date__gte = hoy - timedelta(days=7)
    ).order_by('-created_at')[:5]

    atenciones_semana = Atencion.objects.filter(
        fecha__date__gte=inicio_semana
    ).select_related('cliente').order_by('-fecha')

    def calcular_variacion(hoy, ayer):
        if ayer == 0:
            return "↑ 100%" if hoy > 0 else "0%"
        variacion = ((hoy - ayer) / ayer) * 100
        simbolo = "↑" if variacion > 0 else ("↓" if variacion < 0 else "=")
        return f'{simbolo} {abs(variacion):.1f}%'

    def admin_link(url_name, obj_id, label):
        return format_html(
            '<a href="{}">{}</a>',
            reverse(url_name, args=[obj_id]),
            label
        )

    context.update({
        'kpi': [

            {
                'title': 'Ingresos ventas hoy',
                'metric': f'${ventas_hoy:,.2f}',
                'footer': f'Vs ayer: {calcular_variacion(ventas_hoy, ventas_ayer)} | Mes: ${ventas_mes:,.2f}',
            },
            {
                'title': 'Ingresos atenciones hoy',
                'metric': f'${ingresos_atenciones_hoy:,.2f}',
                'footer': f'Vs ayer: {calcular_variacion(ingresos_atenciones_hoy, ingresos_atenciones_ayer)} | Mes: ${ingresos_atenciones_mes:,.2f}',
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
            "headers": ["Hora", "Cliente", "Empleado", "Servicios", "Estado"],
            "rows": [
                [
                    timezone.localtime(r.fecha_turno).strftime('%H:%M'),
                    admin_link("admin:inventory_cliente_change", r.cliente.pk, str(r.cliente)),
                    admin_link('admin:inventory_reserva_change', r.pk, r.empleado.nombre if r.empleado else '-'),
                    ", ".join(s.nombre for s in r.servicios.all()) or '-',
                    r.estado_badge(),
                ]
                for r in reservas_hoy
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
                    admin_link(
                        "admin:inventory_cliente_change",
                        a.cliente.pk,
                        str(a.cliente),
                    ),
                    admin_link(
                        "admin:inventory_atencion_change",
                        a.pk,
                        ", ".join(s.nombre for s in a.servicios.all()) or '-',
                    ),
                    admin_link(
                        "admin:inventory_atencion_change",
                        a.pk,
                        a.fecha.strftime("%d/%m %H:%M"),
                    ),
                    admin_link(
                        "admin:inventory_atencion_change",
                        a.pk,
                        f"${a.total:,.2f}",
                    ),
                ]
                for a in atenciones_semana
            ],
        },
        "alertas": [
        {
            "mensaje": f"Stock crítico: {p.nombre} ({p.stock} unidades)",
            "nivel": "danger" if p.stock == 0 else "warning",
            "link": reverse("admin:inventory_producto_change", args=[p.pk])
        } for p in stock_bajo
    ],
    })
    return context