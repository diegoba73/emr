# Ejemplo: laboratorio/forms.py
from django import forms
from django.urls import reverse_lazy
# from .models import SolicitudExamen # El modelo de tu SolicitudExamen

class SolicitudExamenAdminForm(forms.ModelForm):
    # class Meta:
    #     model = SolicitudExamen
    #     fields = '__all__'
        # widgets = {
        #     'consulta_asociada': forms.Select(attrs={'data-ajax--url': reverse_lazy('autocomplete_consultas_filtradas')})
        # } # Esto es si no usas AutocompleteSelect por defecto.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estás usando el AutocompleteSelect widget por defecto de Django admin,
        # es más fácil modificarlo en el JavaScript o directamente en el ModelAdmin.
        # Esta aproximación de abajo es para cuando el widget ya es un AutocompleteSelect.
        if 'consulta_asociada' in self.fields and hasattr(self.fields['consulta_asociada'].widget, 'attrs'):
             self.fields['consulta_asociada'].widget.attrs['data-ajax--url'] = reverse_lazy('autocomplete_consultas_filtradas')