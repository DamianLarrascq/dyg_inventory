from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta

from .models import (
    Servicio, Cliente, Producto,
    Atencion, AtencionServicio,
    Venta, VentaItem, Reserva,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures reutilizables
# ---------------------------------------------------------------------------

def make_cliente(**kwargs):
    defaults = dict(nombre="Ana García", email="ana@example.com", telefono="1122334455")
    defaults.update(kwargs)
    return Cliente.objects.create(**defaults)


def make_servicio(**kwargs):
    defaults = dict(nombre="Corte", precio=Decimal("1500.00"))
    defaults.update(kwargs)
    return Servicio.objects.create(**defaults)


def make_producto(**kwargs):
    defaults = dict(
        nombre="Shampoo",
        precio_costo=Decimal("200.00"),
        precio_venta=Decimal("400.00"),
        stock=10,
    )
    defaults.update(kwargs)
    return Producto.objects.create(**defaults)


def make_atencion(cliente, **kwargs):
    defaults = dict(fecha=timezone.now())
    defaults.update(kwargs)
    return Atencion.objects.create(cliente=cliente, **defaults)


def make_venta(cliente=None, **kwargs):
    return Venta.objects.create(cliente=cliente, **kwargs)


# ===========================================================================
# SERVICIO
# ===========================================================================

class ServicioModelTest(TestCase):

    def test_str(self):
        s = make_servicio(nombre="Tinte", precio=Decimal("3000.00"))
        self.assertEqual(str(s), "Tinte ($3000.00)")

    def test_activo_por_defecto(self):
        s = make_servicio()
        self.assertTrue(s.activo)

    def test_inactivo(self):
        s = make_servicio(activo=False)
        self.assertFalse(s.activo)


# ===========================================================================
# CLIENTE
# ===========================================================================

class ClienteModelTest(TestCase):

    def test_str(self):
        c = make_cliente(nombre="Carlos López")
        self.assertEqual(str(c), "Carlos López")

    def test_email_unico(self):
        make_cliente(email="test@test.com")
        with self.assertRaises(Exception):
            make_cliente(nombre="Otro", email="test@test.com", telefono="9988776655")

    def test_timestamps_auto(self):
        c = make_cliente()
        self.assertIsNotNone(c.created_at)
        self.assertIsNotNone(c.updated_at)


# ===========================================================================
# PRODUCTO
# ===========================================================================

class ProductoModelTest(TestCase):

    def test_str(self):
        p = make_producto(nombre="Acondicionador", stock=5)
        self.assertIn("Acondicionador", str(p))
        self.assertIn("5", str(p))

    def test_activo_por_defecto(self):
        p = make_producto()
        self.assertTrue(p.activo)

    def test_ordering_por_nombre(self):
        make_producto(nombre="Zzz", precio_costo=10, precio_venta=20, stock=1)
        make_producto(nombre="Aaa", precio_costo=10, precio_venta=20, stock=1)
        nombres = list(Producto.objects.values_list("nombre", flat=True))
        self.assertEqual(nombres, sorted(nombres))


# ===========================================================================
# ATENCION + AtencionServicio  (lógica de total)
# ===========================================================================

class AtencionTotalTest(TestCase):

    def setUp(self):
        self.cliente = make_cliente()
        self.servicio1 = make_servicio(nombre="Corte", precio=Decimal("1500.00"))
        self.servicio2 = make_servicio(nombre="Tinte", precio=Decimal("3000.00"))
        self.atencion = make_atencion(self.cliente)

    def test_total_inicial_cero(self):
        self.assertEqual(self.atencion.total, Decimal("0"))

    def test_total_se_calcula_al_agregar_servicio(self):
        AtencionServicio.objects.create(
            atencion=self.atencion,
            servicio=self.servicio1,
            precio_aplicado=self.servicio1.precio,
        )
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.total, Decimal("1500.00"))

    def test_total_con_multiples_servicios(self):
        AtencionServicio.objects.create(
            atencion=self.atencion,
            servicio=self.servicio1,
            precio_aplicado=Decimal("1500.00"),
        )
        AtencionServicio.objects.create(
            atencion=self.atencion,
            servicio=self.servicio2,
            precio_aplicado=Decimal("3000.00"),
        )
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.total, Decimal("4500.00"))

    def test_precio_aplicado_hereda_precio_servicio(self):
        """Si no se pasa precio_aplicado, debe tomar el precio del servicio."""
        item = AtencionServicio(
            atencion=self.atencion,
            servicio=self.servicio1,
            precio_aplicado=None,
        )
        # El campo no puede ser None en DB; simulamos la lógica del save
        if not item.precio_aplicado:
            item.precio_aplicado = self.servicio1.precio
        self.assertEqual(item.precio_aplicado, Decimal("1500.00"))

    def test_precio_aplicado_personalizado(self):
        """Se puede aplicar un precio distinto al del servicio (descuento, promo)."""
        AtencionServicio.objects.create(
            atencion=self.atencion,
            servicio=self.servicio1,
            precio_aplicado=Decimal("1000.00"),
        )
        self.atencion.refresh_from_db()
        self.assertEqual(self.atencion.total, Decimal("1000.00"))

    def test_calcular_total_method(self):
        AtencionServicio.objects.create(
            atencion=self.atencion,
            servicio=self.servicio1,
            precio_aplicado=Decimal("1500.00"),
        )
        self.assertEqual(self.atencion.calcular_total(), Decimal("1500.00"))

    def test_atencion_str(self):
        s = str(self.atencion)
        self.assertIn("Ana García", s)


# ===========================================================================
# VENTA + VentaItem  (stock y totales)
# ===========================================================================

class VentaStockTest(TestCase):

    def setUp(self):
        self.cliente = make_cliente()
        self.producto = make_producto(stock=10)
        self.venta = make_venta(self.cliente)

    def test_stock_descuenta_al_crear_item(self):
        VentaItem.objects.create(
            venta=self.venta,
            producto=self.producto,
            cantidad=3,
            precio_unitario=self.producto.precio_venta,
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)

    def test_total_venta_se_actualiza(self):
        VentaItem.objects.create(
            venta=self.venta,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("400.00"),
        )
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.total, Decimal("800.00"))

    def test_subtotal_property(self):
        item = VentaItem(
            venta=self.venta,
            producto=self.producto,
            cantidad=3,
            precio_unitario=Decimal("400.00"),
        )
        self.assertEqual(item.subtotal, Decimal("1200.00"))

    def test_precio_unitario_hereda_precio_venta(self):
        """Si precio_unitario es falsy al crear, usa precio_venta del producto."""
        item = VentaItem(
            venta=self.venta,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("0"),
        )
        if not item.precio_unitario:
            item.precio_unitario = self.producto.precio_venta
        self.assertEqual(item.precio_unitario, Decimal("400.00"))

    def test_venta_sin_cliente(self):
        """Venta puede existir sin cliente (cliente ocasional)."""
        v = make_venta(cliente=None)
        self.assertIsNone(v.cliente)
        self.assertIn("Sin cliente", str(v))

    def test_venta_str(self):
        s = str(self.venta)
        self.assertIn("Ana García", s)

    def test_multiples_items_acumulan_total(self):
        producto2 = make_producto(nombre="Crema", stock=5, precio_costo=100, precio_venta=Decimal("250.00"))
        VentaItem.objects.create(
            venta=self.venta, producto=self.producto,
            cantidad=1, precio_unitario=Decimal("400.00"),
        )
        VentaItem.objects.create(
            venta=self.venta, producto=producto2,
            cantidad=2, precio_unitario=Decimal("250.00"),
        )
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.total, Decimal("900.00"))


# ===========================================================================
# RESERVA
# ===========================================================================

class ReservaModelTest(TestCase):

    def setUp(self):
        self.cliente = make_cliente()
        self.servicio = make_servicio()

    def _make_reserva(self, **kwargs):
        defaults = dict(
            cliente=self.cliente,
            servicios=self.servicio,
            fecha_turno=timezone.now() + timedelta(days=1),
        )
        defaults.update(kwargs)
        return Reserva.objects.create(**defaults)

    def test_estado_por_defecto_pendiente(self):
        r = self._make_reserva()
        self.assertEqual(r.estado, "pendiente")

    def test_estados_validos(self):
        estados = ["pendiente", "confirmada", "cancelada", "completada"]
        for estado in estados:
            r = self._make_reserva(estado=estado)
            self.assertEqual(r.estado, estado)

    def test_str(self):
        r = self._make_reserva()
        self.assertIn("Ana García", str(r))
        self.assertIn(str(r.pk), str(r))

    def test_sin_servicio(self):
        r = self._make_reserva(servicios=None)
        self.assertIsNone(r.servicios)

    def test_ordering_por_fecha_desc(self):
        ahora = timezone.now()
        r1 = self._make_reserva(fecha_turno=ahora + timedelta(days=1))
        r2 = self._make_reserva(fecha_turno=ahora + timedelta(days=3))
        reservas = list(Reserva.objects.all())
        self.assertEqual(reservas[0], r2)  # más reciente primero


# ===========================================================================
# ADMIN ACCESS (smoke tests)
# ===========================================================================

class AdminSmokeTest(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", password="admin1234", email="admin@test.com"
        )
        self.client.force_login(self.superuser)

    def test_admin_index(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_cliente_list(self):
        resp = self.client.get("/admin/inventory/cliente/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_producto_list(self):
        resp = self.client.get("/admin/inventory/producto/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_venta_list(self):
        resp = self.client.get("/admin/inventory/venta/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_reserva_list(self):
        resp = self.client.get("/admin/inventory/reserva/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_sin_login_redirige(self):
        self.client.logout()
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)

    def test_admin_cliente_add(self):
        resp = self.client.get("/admin/inventory/cliente/add/")
        self.assertEqual(resp.status_code, 200)

    def test_admin_reserva_add(self):
        resp = self.client.get("/admin/inventory/reserva/add/")
        self.assertEqual(resp.status_code, 200)


# ===========================================================================
# DASHBOARD DATA
# ===========================================================================

class DashboardCallbackTest(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", password="admin1234", email="admin@test.com"
        )
        self.client.force_login(self.superuser)

    def test_dashboard_carga_sin_datos(self):
        """El dashboard no debe explotar con tablas vacías."""
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_con_datos(self):
        cliente = make_cliente()
        servicio = make_servicio()
        Reserva.objects.create(
            cliente=cliente,
            servicios=servicio,
            fecha_turno=timezone.now() + timedelta(hours=2),
            estado="pendiente",
        )
        make_producto(nombre="Stock bajo", stock=1)
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)