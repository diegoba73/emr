from django.test import SimpleTestCase
from laboratorio.models_inventario import InsumoLab
from laboratorio.management.commands.import_catalogo_reactivos_csv import planificar


def row(photo='47', name='Urea UV cinética AA líquida', ref='1008108', **extra):
    return {'ID foto': photo, 'Producto (etiqueta)': name, 'Fabricante / marca': 'Wiener lab.',
            'REF comercial': ref, 'Clase': 'Reactivo', **extra}


class ImportCatalogoTests(SimpleTestCase):
    def test_deduplica_lotes_y_preserva_sku(self):
        obj = InsumoLab(id=22, codigo='R-1008108', nombre='Wiener Urea', ref_comercial='1008108')
        plan = planificar([row(), row(photo='49')], [obj])
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['id'], 22)
        self.assertEqual(set(plan[0]['cambios']), {'nombre'})
        self.assertEqual(len(plan[0]['fuente']), 2)

    def test_corrige_ref_sin_cambiar_sku_y_es_idempotente(self):
        obj = InsumoLab(id=19, codigo='R-1009804', nombre='Wiener HDL Cholesterol fast', ref_comercial='1009804')
        rows = [row(photo='48', name='HDL Cholesterol fast', ref='1008102')]
        first = planificar(rows, [obj])[0]
        self.assertEqual(first['cambios'], {'ref_comercial': '1008102'})
        obj.ref_comercial = '1008102'
        self.assertEqual(planificar(rows, [obj])[0]['accion'], 'sin_cambios')

    def test_no_reemplaza_creatinina_de_otro_metodo(self):
        obj = InsumoLab(id=17, codigo='R-1008149', nombre='Wiener Creatinina enzimática', ref_comercial='1008149')
        p = planificar([row(photo='1', name='Creatinina cinética AA líquida', ref='1260360')], [obj])[0]
        self.assertEqual(p['accion'], 'crear')
        self.assertEqual(p['codigo'], 'R-1260360')

    def test_ref_dudosa_no_se_importa_y_repetir_no_duplica(self):
        rows = [row(photo='29', name='BG10', ref='69444138')]
        p = planificar(rows, [])[0]
        self.assertEqual(p['cambios']['ref_comercial'], '')
        obj = InsumoLab(id=99, **p['cambios'])
        self.assertEqual(planificar(rows, [obj])[0]['accion'], 'sin_cambios')

    def test_ref_duplicada_aborta(self):
        from django.core.management.base import CommandError
        objs = [InsumoLab(id=i, codigo=str(i), ref_comercial='1008108') for i in (1, 2)]
        with self.assertRaises(CommandError):
            planificar([row()], objs)
