from django.utils import timezone
from datetime import timedelta
from .models import Reserva, Venta, Producto, Cliente


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

    ingresos_hoy = sum(
        v.total for v in Venta.objects.filter(fecha__date=hoy)
    )
    ingresos_mes = sum(
        v.total for v in Venta.objects.filter(fecha__date__gte=inicio_mes)
    )

    stock_bajo = Producto.objects.filter(stock__lte=3, activo=True).order_by('stock')

    clientes_nuevos = Cliente.objects.filter(
        created_at__date__gte = hoy - timedelta(days=7)
    ).order_by('-created_at')[:5]

    context.update({
        'kpi': [
            {
                'title': 'Reservas hoy',
                'metric': reservas_hoy,
                'footer': f'Semana: {reservas_semana.count()}',
            },
            {
                'title': 'Ingresos hoy',
                'metric': f'${ingresos_hoy:,.2f}',
                'footer': f'Mes: ${ingresos_mes:,.2f}',
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
        'reservas_semana': reservas_semana.select_related('cliente', 'servicios').order_by('fecha_turno'),
        'stock_bajo': stock_bajo,
        'clientes_nuevos': clientes_nuevos,

                "tabla_reservas": {
        "headers": ["Cliente", "Servicio", "Fecha", "Estado"],
        "rows": [
            [
                str(r.cliente),
                str(r.servicios) if r.servicios else "-",
                r.fecha_turno.strftime("%d/%m %H:%M"),
                r.get_estado_display(),
            ]
            for r in reservas_semana
        ],
    },
    "tabla_stock": {
        "headers": ["Producto", "Stock"],
        "rows": [[p.nombre, p.stock] for p in stock_bajo],
    },
    "tabla_clientes": {
        "headers": ["Nombre", "Teléfono", "Fecha de alta"],
        "rows": [
            [c.nombre, c.telefono, c.created_at.strftime("%d/%m/%Y")]
            for c in clientes_nuevos
        ],
    },
    },
    )
    return context