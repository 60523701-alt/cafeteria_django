# Importamos el administrador de Django.
from django.contrib import admin
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
# Importamos nuestros modelos.
from .models import (
    Categoria,
    Producto,
    Pedido,
    DetallePedido,
)


# =========================================================
# ADMINISTRACIÓN DE CATEGORÍAS
# =========================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):

    # Columnas visibles en la lista.
    list_display = (
        "nombre",
        "activo",
    )

    # Campo utilizado por el buscador.
    search_fields = (
        "nombre",
    )

    # Filtros laterales.
    list_filter = (
        "activo",
    )


# =========================================================
# ADMINISTRACIÓN DE PRODUCTOS
# =========================================================

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):

    # Columnas visibles.
    list_display = (
        "nombre",
        "categoria",
        "precio",
        "stock",
        "activo",
    )

    # Permite editar algunos campos directamente
    # desde la lista de productos.
    list_editable = (
        "precio",
        "stock",
        "activo",
    )

    # Buscador.
    search_fields = (
        "nombre",
        "descripcion",
    )

    # Filtros.
    list_filter = (
        "categoria",
        "activo",
    )

    # Orden alfabético.
    ordering = (
        "nombre",
    )


# =========================================================
# DETALLES DENTRO DEL PEDIDO
# =========================================================

class DetallePedidoInline(admin.TabularInline):

    # Modelo que aparecerá dentro del pedido.
    model = DetallePedido

    # No crear filas vacías adicionales.
    extra = 0

    # Campos que se visualizarán.
    fields = (
        "producto",
        "cantidad",
        "precio_unitario",
    )



# =========================================================
# ADMINISTRACIÓN DE PEDIDOS
# =========================================================

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "usuario",
        "fecha",
        "total",
        "estado",
    )

    search_fields = (
        "usuario__username",
    )

    list_filter = (
        "estado",
        "fecha",
    )

    # Los detalles se mostrarán dentro del pedido.
    inlines = [
        DetallePedidoInline,
    ]
    
    # Actualizar el inventario al modificar los detalles.
    def save_formset(self, request, form, formset, change):

        # Aplicar este control solamente a los detalles del pedido.
        if formset.model != DetallePedido:
            return super().save_formset(
                request, form, formset, change
            )

        pedido = form.instance

        with transaction.atomic():

            # Guardar temporalmente las cantidades originales.
            originales = {
                detalle.id: (
                    detalle.producto_id,
                    detalle.cantidad,
                )
                for detalle in DetallePedido.objects.filter(
                    pedido=pedido
                )
            }

            # Obtener los detalles modificados y eliminados.
            instancias = formset.save(commit=False)
            eliminados = list(formset.deleted_objects)

            # Calcular las diferencias de inventario.
            diferencias = {}

            def acumular(producto_id, cantidad):
                diferencias[producto_id] = (
                    diferencias.get(producto_id, 0) + cantidad
                )

            # Procesar detalles modificados o nuevos.
            for detalle in instancias:

                if detalle.pk in originales:
                    producto_anterior, cantidad_anterior = (
                        originales[detalle.pk]
                    )

                    # Devolver la cantidad anterior.
                    acumular(
                        producto_anterior,
                        cantidad_anterior,
                    )

                # Descontar la nueva cantidad.
                acumular(
                    detalle.producto_id,
                    -detalle.cantidad,
                )

            # Procesar detalles eliminados.
            for detalle in eliminados:
                producto_id, cantidad = originales[detalle.pk]

                acumular(producto_id, cantidad)

            # No permitir modificar cantidades en pedidos
            # que no estén pendientes o tengan stock devuelto.
            if diferencias and (
                pedido.estado != Pedido.Estado.PENDIENTE
                or pedido.inventario_devuelto
            ):
                raise ValidationError(
                    "Solo se pueden modificar los detalles "
                    "de pedidos pendientes."
                )

            # Actualizar el inventario.
            for producto_id, diferencia in sorted(
                diferencias.items()
            ):

                producto = Producto.objects.select_for_update().get(
                    id=producto_id
                )

                # Comprobar disponibilidad.
                if producto.stock + diferencia < 0:
                    raise ValidationError(
                        f"Stock insuficiente para {producto.nombre}. "
                        f"Disponible: {producto.stock}."
                    )

                producto.stock += diferencia

                producto.save(update_fields=["stock"])

            # Guardar los detalles modificados o nuevos.
            for detalle in instancias:
                detalle.save()

            # Eliminar los detalles correspondientes.
            for detalle in eliminados:
                detalle.delete()

            formset.save_m2m()

    # Recalcular el total después de guardar los detalles.
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        pedido = form.instance

        detalles = pedido.detalles.all()

        pedido.total = sum(
            (
                detalle.precio_unitario * detalle.cantidad
                for detalle in detalles
            ),
            Decimal("0.00"),
        )

        pedido.save(update_fields=["total"])

# =========================================================
# ADMINISTRACIÓN DE DETALLES
# =========================================================

@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):

    # Columnas visibles.
    list_display = (
        "pedido",
        "producto",
        "cantidad",
        "precio_unitario",
    )

    # Campos que pueden buscarse.
    search_fields = (
        "producto__nombre",
        "pedido__usuario__username",
    )
