from django import forms
from django.core.validators import MinValueValidator

class LoginForm(forms.Form):
    nombre_usuario = forms.CharField(label='Usuario', max_length=100)
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)

class RegistrarOrdenForm(forms.Form):
    numero_orden = forms.IntegerField(
        label='Numero de orden',
        min_value=1,
        error_messages={
            'required': 'El numero de orden es obligatorio',
            'min_value': 'El numero debe ser positivo'
        },
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 2002'
        })
    )

    fecha = forms.DateField(
        label='Fecha de la orden',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    obra_input = forms.CharField(
        label='Obra',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'list': 'obra_list',
            'class': 'form-control',
            'placeholder': 'Selecciona una obra'
        })
    )

    solicitante_input = forms.CharField(
        label='Solicitante',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'list': 'solicitante_list',
            'class': 'form-control'
        })
    )

    estatus_input = forms.CharField(
        label='Estatus',
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'list': 'estatus_list',
            'class': 'form-control'
        })
    )
    
    # SIMPLIFICADO: CharField en lugar de ChoiceField
    metodo_pago = forms.CharField(
        label='Método de pago',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'list': 'metodo_pago_list',  # Usando datalist como los demás
            'class': 'form-control',
            'placeholder': 'Selecciona método de pago'
        })
    )