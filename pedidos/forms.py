# =========================================================
# FORMULARIOS DEL SISTEMA
# =========================================================

# Sistema de formularios de Django.
from django import forms

# Modelos que utilizaremos dentro de los formularios.
from .models import Categoria, Pedido, DetallePedido


# =========================================================
# FORMULARIO PARA BUSCAR PRODUCTOS
# =========================================================

class ProductoFiltroForm(forms.Form):

    # -----------------------------------------------------
    # BÚSQUEDA POR NOMBRE
    # -----------------------------------------------------

    # Campo de texto opcional.
    busqueda = forms.CharField(
        required=False,
        label="Buscar producto",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: café",
            }
        ),
    )


    # -----------------------------------------------------
    # FILTRO POR CATEGORÍA
    # -----------------------------------------------------

    # ModelChoiceField permite llenar automáticamente
    # el selector utilizando objetos de Categoria.
    categoria = forms.ModelChoiceField(
        required=False,

        # Solo mostramos categorías activas.
        queryset=Categoria.objects.filter(
            activo=True
        ).order_by("nombre"),

        # Opción utilizada cuando no queremos
        # filtrar por una categoría específica.
        empty_label="Todas las categorías",

        label="Categoría",

        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

# =========================================================
# FORMULARIO PARA FILTRAR REPORTES
# =========================================================

class ReporteFiltroForm(forms.Form):

    # Fecha inicial.
    #
    # required=False significa que el filtro
    # puede quedar vacío.
    fecha_desde = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    # Fecha final.
    fecha_hasta = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    # Estado del pedido.
    #
    # Agregamos primero una opción vacía
    # para representar "Todos".
    estado = forms.ChoiceField(
        required=False,
        label="Estado",
        choices=[
            ("", "Todos"),
            *Pedido.Estado.choices,
        ],
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    # =====================================================
    # VALIDACIÓN DEL FORMULARIO
    # =====================================================

    def clean(self):

        # Ejecutamos primero las validaciones
        # proporcionadas por Django.
        datos = super().clean()

        fecha_desde = datos.get("fecha_desde")

        fecha_hasta = datos.get("fecha_hasta")

        # Comprobamos que la fecha inicial
        # no sea posterior a la fecha final.
        if (
            fecha_desde
            and fecha_hasta
            and fecha_desde > fecha_hasta
        ):

            raise forms.ValidationError(
                "La fecha inicial no puede ser "
                "posterior a la fecha final."
            )

        return datos
# =========================================================
# FORMULARIO PARA EDITAR CANTIDADES DE UN PEDIDO
# =========================================================

class CantidadDetalleForm(forms.ModelForm):

    class Meta:
        model = DetallePedido

        fields = ["cantidad"]

        widgets = {
            "cantidad": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
        }

    def clean_cantidad(self):

        cantidad = self.cleaned_data.get("cantidad")

        # No permitir cantidades menores a uno.
        if cantidad < 1:
            raise forms.ValidationError(
                "La cantidad debe ser como mínimo 1."
            )

        # Solo se pueden modificar pedidos pendientes.
        if self.instance.pedido.estado != Pedido.Estado.PENDIENTE:
            raise forms.ValidationError(
                "Solo se pueden modificar pedidos pendientes."
            )

        return cantidad
# =========================================================
# FORMULARIO PARA CAMBIAR EL ESTADO DEL PEDIDO
# =========================================================


class PedidoEstadoForm(forms.Form):

    estado = forms.ChoiceField(
        label="Cambiar estado",
        choices=Pedido.Estado.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, pedido=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.pedido = pedido

        if self.pedido is not None:

            estados_permitidos = [
                self.pedido.estado,
                *self.pedido.estados_siguientes(),
            ]

            self.fields["estado"].choices = [
                (valor, etiqueta)
                for valor, etiqueta in Pedido.Estado.choices
                if valor in estados_permitidos
            ]

    def clean_estado(self):

        nuevo_estado = self.cleaned_data.get("estado")

        if self.pedido is None:

            raise forms.ValidationError(
                "No se encontró el pedido."
            )

        if nuevo_estado != self.pedido.estado:

            if nuevo_estado not in self.pedido.estados_siguientes():

                raise forms.ValidationError(
                    "No está permitido realizar este cambio de estado."
                )

        return nuevo_estado
