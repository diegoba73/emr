"""
Management command para poblar medicamentos con datos reales
de medicamentos comercializados en Argentina.
"""
from django.core.management.base import BaseCommand
from catalogos.models import Medicamento


class Command(BaseCommand):
    help = 'Pobla la base de datos con medicamentos reales comercializados en Argentina'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todos los medicamentos existentes antes de poblar',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Eliminando medicamentos existentes...')
            Medicamento.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Medicamentos eliminados'))

        # Medicamentos reales comercializados en Argentina
        medicamentos = [
            # ANTIHIPERTENSIVOS
            {
                'nombre': 'Losartán',
                'principio_activo': 'Losartán potásico',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09CA01'
            },
            {
                'nombre': 'Losartán',
                'principio_activo': 'Losartán potásico',
                'presentacion': 'Comprimidos',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09CA01'
            },
            {
                'nombre': 'Enalapril',
                'principio_activo': 'Enalapril maleato',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09AA02'
            },
            {
                'nombre': 'Enalapril',
                'principio_activo': 'Enalapril maleato',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09AA02'
            },
            {
                'nombre': 'Amlodipino',
                'principio_activo': 'Amlodipino besilato',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C08CA01'
            },
            {
                'nombre': 'Amlodipino',
                'principio_activo': 'Amlodipino besilato',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C08CA01'
            },
            {
                'nombre': 'Carvedilol',
                'principio_activo': 'Carvedilol',
                'presentacion': 'Comprimidos',
                'concentracion': '25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C07AG02'
            },
            {
                'nombre': 'Metoprolol',
                'principio_activo': 'Metoprolol tartrato',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C07AB02'
            },
            {
                'nombre': 'Metoprolol',
                'principio_activo': 'Metoprolol tartrato',
                'presentacion': 'Comprimidos',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C07AB02'
            },
            {
                'nombre': 'Bisoprolol',
                'principio_activo': 'Bisoprolol fumarato',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C07AB07'
            },
            {
                'nombre': 'Hidroclorotiazida',
                'principio_activo': 'Hidroclorotiazida',
                'presentacion': 'Comprimidos',
                'concentracion': '25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C03AA03'
            },
            
            # ESTATINAS (HIPOLIPEMIANTES)
            {
                'nombre': 'Atorvastatina',
                'principio_activo': 'Atorvastatina cálcica',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA05'
            },
            {
                'nombre': 'Atorvastatina',
                'principio_activo': 'Atorvastatina cálcica',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA05'
            },
            {
                'nombre': 'Atorvastatina',
                'principio_activo': 'Atorvastatina cálcica',
                'presentacion': 'Comprimidos',
                'concentracion': '40 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA05'
            },
            {
                'nombre': 'Rosuvastatina',
                'principio_activo': 'Rosuvastatina cálcica',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA07'
            },
            {
                'nombre': 'Rosuvastatina',
                'principio_activo': 'Rosuvastatina cálcica',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA07'
            },
            {
                'nombre': 'Simvastatina',
                'principio_activo': 'Simvastatina',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA01'
            },
            {
                'nombre': 'Simvastatina',
                'principio_activo': 'Simvastatina',
                'presentacion': 'Comprimidos',
                'concentracion': '40 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10AA01'
            },
            
            # ANTIPLAQUETARIOS Y ANTICOAGULANTES
            {
                'nombre': 'Ácido Acetilsalicílico',
                'principio_activo': 'Ácido acetilsalicílico',
                'presentacion': 'Comprimidos',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AC06'
            },
            {
                'nombre': 'Clopidogrel',
                'principio_activo': 'Clopidogrel bisulfato',
                'presentacion': 'Comprimidos',
                'concentracion': '75 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AC04'
            },
            {
                'nombre': 'Ticagrelor',
                'principio_activo': 'Ticagrelor',
                'presentacion': 'Comprimidos',
                'concentracion': '90 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AC24'
            },
            {
                'nombre': 'Warfarina',
                'principio_activo': 'Warfarina sódica',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AA03'
            },
            {
                'nombre': 'Apixabán',
                'principio_activo': 'Apixabán',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AF02'
            },
            {
                'nombre': 'Rivaroxabán',
                'principio_activo': 'Rivaroxabán',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AF01'
            },
            {
                'nombre': 'Enoxaparina',
                'principio_activo': 'Enoxaparina sódica',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '40 mg/0.4 ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'B01AB05'
            },
            {
                'nombre': 'Enoxaparina',
                'principio_activo': 'Enoxaparina sódica',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '60 mg/0.6 ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'B01AB05'
            },
            {
                'nombre': 'Heparina Sódica',
                'principio_activo': 'Heparina sódica',
                'presentacion': 'Ampolla',
                'concentracion': '5000 UI/ml',
                'via_administracion': 'Intravenosa/Subcutánea',
                'codigo_atc': 'B01AB01'
            },
            
            # DIURÉTICOS
            {
                'nombre': 'Furosemida',
                'principio_activo': 'Furosemida',
                'presentacion': 'Comprimidos',
                'concentracion': '40 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C03CA01'
            },
            {
                'nombre': 'Furosemida',
                'principio_activo': 'Furosemida',
                'presentacion': 'Ampolla',
                'concentracion': '20 mg/2 ml',
                'via_administracion': 'Intravenosa/Intramuscular',
                'codigo_atc': 'C03CA01'
            },
            {
                'nombre': 'Espironolactona',
                'principio_activo': 'Espironolactona',
                'presentacion': 'Comprimidos',
                'concentracion': '25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C03DA01'
            },
            {
                'nombre': 'Espironolactona',
                'principio_activo': 'Espironolactona',
                'presentacion': 'Comprimidos',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C03DA01'
            },
            
            # DIGITALES
            {
                'nombre': 'Digoxina',
                'principio_activo': 'Digoxina',
                'presentacion': 'Comprimidos',
                'concentracion': '0.25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01AA05'
            },
            
            # ANTIARRÍTMICOS
            {
                'nombre': 'Amiodarona',
                'principio_activo': 'Amiodarona clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01BD01'
            },
            {
                'nombre': 'Amiodarona',
                'principio_activo': 'Amiodarona clorhidrato',
                'presentacion': 'Ampolla',
                'concentracion': '150 mg/3 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'C01BD01'
            },
            {
                'nombre': 'Flecainida',
                'principio_activo': 'Flecainida acetato',
                'presentacion': 'Comprimidos',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01BC04'
            },
            {
                'nombre': 'Propafenona',
                'principio_activo': 'Propafenona clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '150 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01BC03'
            },
            
            # NITRATOS
            {
                'nombre': 'Mononitrato de Isosorbida',
                'principio_activo': 'Mononitrato de isosorbida',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01DA14'
            },
            {
                'nombre': 'Dinitrato de Isosorbida',
                'principio_activo': 'Dinitrato de isosorbida',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Sublingual',
                'codigo_atc': 'C01DA08'
            },
            {
                'nombre': 'Nitroglicerina',
                'principio_activo': 'Nitroglicerina',
                'presentacion': 'Comprimidos',
                'concentracion': '0.5 mg',
                'via_administracion': 'Sublingual',
                'codigo_atc': 'C01DA02'
            },
            {
                'nombre': 'Nitroglicerina',
                'principio_activo': 'Nitroglicerina',
                'presentacion': 'Spray',
                'concentracion': '0.4 mg/dosis',
                'via_administracion': 'Sublingual',
                'codigo_atc': 'C01DA02'
            },
            
            # ANTAGONISTAS DEL CALCIO
            {
                'nombre': 'Diltiazem',
                'principio_activo': 'Diltiazem clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '60 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C08DB01'
            },
            {
                'nombre': 'Verapamilo',
                'principio_activo': 'Verapamilo clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '80 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C08DA01'
            },
            
            # INHIBIDORES DE LA ENZIMA CONVERTIDORA (IECA)
            {
                'nombre': 'Captopril',
                'principio_activo': 'Captopril',
                'presentacion': 'Comprimidos',
                'concentracion': '25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09AA01'
            },
            {
                'nombre': 'Ramipril',
                'principio_activo': 'Ramipril',
                'presentacion': 'Cápsulas',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09AA05'
            },
            {
                'nombre': 'Lisinopril',
                'principio_activo': 'Lisinopril dihidratado',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09AA03'
            },
            
            # ANTAGONISTAS DE RECEPTORES DE ANGIOTENSINA II (ARA II)
            {
                'nombre': 'Valsartán',
                'principio_activo': 'Valsartán',
                'presentacion': 'Comprimidos',
                'concentracion': '160 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09CA03'
            },
            {
                'nombre': 'Irbesartán',
                'principio_activo': 'Irbesartán',
                'presentacion': 'Comprimidos',
                'concentracion': '150 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09CA04'
            },
            {
                'nombre': 'Candesartán',
                'principio_activo': 'Candesartán cilexetilo',
                'presentacion': 'Comprimidos',
                'concentracion': '16 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09CA06'
            },
            
            # ANTIDIABÉTICOS
            {
                'nombre': 'Metformina',
                'principio_activo': 'Metformina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A10BA02'
            },
            {
                'nombre': 'Metformina',
                'principio_activo': 'Metformina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '850 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A10BA02'
            },
            {
                'nombre': 'Glibenclamida',
                'principio_activo': 'Glibenclamida',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A10BB01'
            },
            {
                'nombre': 'Gliclazida',
                'principio_activo': 'Gliclazida',
                'presentacion': 'Comprimidos',
                'concentracion': '80 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A10BB09'
            },
            {
                'nombre': 'Insulina NPH',
                'principio_activo': 'Insulina humana isofánica',
                'presentacion': 'Vial',
                'concentracion': '100 UI/ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'A10AC01'
            },
            {
                'nombre': 'Insulina Regular',
                'principio_activo': 'Insulina humana regular',
                'presentacion': 'Vial',
                'concentracion': '100 UI/ml',
                'via_administracion': 'Subcutánea/Intravenosa',
                'codigo_atc': 'A10AB01'
            },
            {
                'nombre': 'Insulina Glargina',
                'principio_activo': 'Insulina glargina',
                'presentacion': 'Vial',
                'concentracion': '100 UI/ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'A10AE04'
            },
            
            # ANTIBIÓTICOS
            {
                'nombre': 'Amoxicilina',
                'principio_activo': 'Amoxicilina trihidratado',
                'presentacion': 'Cápsulas',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'J01CA04'
            },
            {
                'nombre': 'Amoxicilina + Ácido Clavulánico',
                'principio_activo': 'Amoxicilina + Ácido clavulánico',
                'presentacion': 'Comprimidos',
                'concentracion': '875/125 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'J01CR02'
            },
            {
                'nombre': 'Azitromicina',
                'principio_activo': 'Azitromicina dihidratado',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'J01FA10'
            },
            {
                'nombre': 'Ciprofloxacina',
                'principio_activo': 'Ciprofloxacina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'J01MA02'
            },
            {
                'nombre': 'Ceftriaxona',
                'principio_activo': 'Ceftriaxona sódica',
                'presentacion': 'Vial',
                'concentracion': '1 g',
                'via_administracion': 'Intramuscular/Intravenosa',
                'codigo_atc': 'J01DD04'
            },
            
            # ANALGÉSICOS Y ANTIINFLAMATORIOS
            {
                'nombre': 'Paracetamol',
                'principio_activo': 'Paracetamol',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'N02BE01'
            },
            {
                'nombre': 'Paracetamol',
                'principio_activo': 'Paracetamol',
                'presentacion': 'Comprimidos',
                'concentracion': '1 g',
                'via_administracion': 'Oral',
                'codigo_atc': 'N02BE01'
            },
            {
                'nombre': 'Ibuprofeno',
                'principio_activo': 'Ibuprofeno',
                'presentacion': 'Comprimidos',
                'concentracion': '400 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'M01AE01'
            },
            {
                'nombre': 'Ibuprofeno',
                'principio_activo': 'Ibuprofeno',
                'presentacion': 'Comprimidos',
                'concentracion': '600 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'M01AE01'
            },
            {
                'nombre': 'Diclofenac',
                'principio_activo': 'Diclofenac sódico',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'M01AB05'
            },
            {
                'nombre': 'Diclofenac',
                'principio_activo': 'Diclofenac sódico',
                'presentacion': 'Ampolla',
                'concentracion': '75 mg/3 ml',
                'via_administracion': 'Intramuscular',
                'codigo_atc': 'M01AB05'
            },
            {
                'nombre': 'Naproxeno',
                'principio_activo': 'Naproxeno sódico',
                'presentacion': 'Comprimidos',
                'concentracion': '550 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'M01AE02'
            },
            
            # CORTICOESTEROIDES
            {
                'nombre': 'Prednisona',
                'principio_activo': 'Prednisona',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'H02AB06'
            },
            {
                'nombre': 'Metilprednisolona',
                'principio_activo': 'Metilprednisolona',
                'presentacion': 'Comprimidos',
                'concentracion': '16 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'H02AB04'
            },
            {
                'nombre': 'Dexametasona',
                'principio_activo': 'Dexametasona',
                'presentacion': 'Ampolla',
                'concentracion': '8 mg/2 ml',
                'via_administracion': 'Intramuscular/Intravenosa',
                'codigo_atc': 'H02AB02'
            },
            
            # GASTROPROTECTORES
            {
                'nombre': 'Omeprazol',
                'principio_activo': 'Omeprazol',
                'presentacion': 'Cápsulas',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A02BC01'
            },
            {
                'nombre': 'Pantoprazol',
                'principio_activo': 'Pantoprazol sódico',
                'presentacion': 'Comprimidos',
                'concentracion': '40 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A02BC02'
            },
            {
                'nombre': 'Lansoprazol',
                'principio_activo': 'Lansoprazol',
                'presentacion': 'Cápsulas',
                'concentracion': '30 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A02BC03'
            },
            
            # ANTIHISTAMÍNICOS
            {
                'nombre': 'Loratadina',
                'principio_activo': 'Loratadina',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'R06AX13'
            },
            {
                'nombre': 'Cetirizina',
                'principio_activo': 'Cetirizina diclorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'R06AE07'
            },
            
            # BRONCODILATADORES
            {
                'nombre': 'Salbutamol',
                'principio_activo': 'Salbutamol sulfato',
                'presentacion': 'Inhalador',
                'concentracion': '100 mcg/dosis',
                'via_administracion': 'Inhalatoria',
                'codigo_atc': 'R03AC02'
            },
            {
                'nombre': 'Budesonida + Formoterol',
                'principio_activo': 'Budesonida + Formoterol',
                'presentacion': 'Inhalador',
                'concentracion': '160/4.5 mcg/dosis',
                'via_administracion': 'Inhalatoria',
                'codigo_atc': 'R03AK07'
            },
            
            # ANTIDEPRESIVOS
            {
                'nombre': 'Sertralina',
                'principio_activo': 'Sertralina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'N06AB06'
            },
            {
                'nombre': 'Fluoxetina',
                'principio_activo': 'Fluoxetina clorhidrato',
                'presentacion': 'Cápsulas',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'N06AB03'
            },
            
            # ANTICONVULSIVANTES
            {
                'nombre': 'Ácido Valproico',
                'principio_activo': 'Ácido valproico',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'N03AG01'
            },
            {
                'nombre': 'Carbamazepina',
                'principio_activo': 'Carbamazepina',
                'presentacion': 'Comprimidos',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'N03AF01'
            },
            
            # VITAMINAS Y SUPLEMENTOS
            {
                'nombre': 'Ácido Fólico',
                'principio_activo': 'Ácido fólico',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B03BB01'
            },
            {
                'nombre': 'Vitamina D3',
                'principio_activo': 'Colecalciferol',
                'presentacion': 'Cápsulas',
                'concentracion': '2000 UI',
                'via_administracion': 'Oral',
                'codigo_atc': 'A11CC05'
            },
            {
                'nombre': 'Hierro',
                'principio_activo': 'Sulfato ferroso',
                'presentacion': 'Comprimidos',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B03AA07'
            },
            
            # MEDICACIÓN CARDIOLÓGICA ADICIONAL
            {
                'nombre': 'Sacubitrilo + Valsartán',
                'principio_activo': 'Sacubitrilo + Valsartán',
                'presentacion': 'Comprimidos',
                'concentracion': '97/103 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C09DX04'
            },
            {
                'nombre': 'Ivabradina',
                'principio_activo': 'Ivabradina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01EB17'
            },
            {
                'nombre': 'Ivabradina',
                'principio_activo': 'Ivabradina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '7.5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01EB17'
            },
            {
                'nombre': 'Dapagliflozina',
                'principio_activo': 'Dapagliflozina',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10BX05'
            },
            {
                'nombre': 'Empagliflozina',
                'principio_activo': 'Empagliflozina',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C10BX04'
            },
            {
                'nombre': 'Eplerenona',
                'principio_activo': 'Eplerenona',
                'presentacion': 'Comprimidos',
                'concentracion': '25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C03DA04'
            },
            {
                'nombre': 'Eplerenona',
                'principio_activo': 'Eplerenona',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C03DA04'
            },
            {
                'nombre': 'Trimetazidina',
                'principio_activo': 'Trimetazidina clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '35 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01EB15'
            },
            {
                'nombre': 'Ranolazina',
                'principio_activo': 'Ranolazina',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01EB18'
            },
            {
                'nombre': 'Isosorbida Mononitrato',
                'principio_activo': 'Mononitrato de isosorbida',
                'presentacion': 'Comprimidos',
                'concentracion': '40 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01DA14'
            },
            {
                'nombre': 'Nebivolol',
                'principio_activo': 'Nebivolol clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C07AB12'
            },
            {
                'nombre': 'Dabigatrán',
                'principio_activo': 'Dabigatrán etexilato',
                'presentacion': 'Cápsulas',
                'concentracion': '150 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AE07'
            },
            {
                'nombre': 'Edoxabán',
                'principio_activo': 'Edoxabán',
                'presentacion': 'Comprimidos',
                'concentracion': '60 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AF03'
            },
            {
                'nombre': 'Ticagrelor',
                'principio_activo': 'Ticagrelor',
                'presentacion': 'Comprimidos',
                'concentracion': '60 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AC24'
            },
            {
                'nombre': 'Prasugrel',
                'principio_activo': 'Prasugrel clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B01AC22'
            },
            {
                'nombre': 'Dronedarona',
                'principio_activo': 'Dronedarona clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '400 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C01BD07'
            },
            {
                'nombre': 'Sotalol',
                'principio_activo': 'Sotalol clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '80 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C07AA07'
            },
            {
                'nombre': 'Diltiazem',
                'principio_activo': 'Diltiazem clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '120 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C08DB01'
            },
            {
                'nombre': 'Verapamilo',
                'principio_activo': 'Verapamilo clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '240 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'C08DA01'
            },
            
            # MEDICACIÓN GINECOLÓGICA
            {
                'nombre': 'Levonorgestrel',
                'principio_activo': 'Levonorgestrel',
                'presentacion': 'Comprimidos',
                'concentracion': '0.75 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03AC03'
            },
            {
                'nombre': 'Etonogestrel',
                'principio_activo': 'Etonogestrel',
                'presentacion': 'Implante subdérmico',
                'concentracion': '68 mg',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'G03AC08'
            },
            {
                'nombre': 'Medroxiprogesterona',
                'principio_activo': 'Acetato de medroxiprogesterona',
                'presentacion': 'Inyección',
                'concentracion': '150 mg/ml',
                'via_administracion': 'Intramuscular',
                'codigo_atc': 'G03AC06'
            },
            {
                'nombre': 'Medroxiprogesterona',
                'principio_activo': 'Acetato de medroxiprogesterona',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03AC06'
            },
            {
                'nombre': 'Drospirenona + Etinilestradiol',
                'principio_activo': 'Drospirenona + Etinilestradiol',
                'presentacion': 'Comprimidos',
                'concentracion': '3/0.03 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03AA12'
            },
            {
                'nombre': 'Desogestrel + Etinilestradiol',
                'principio_activo': 'Desogestrel + Etinilestradiol',
                'presentacion': 'Comprimidos',
                'concentracion': '0.15/0.03 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03AA09'
            },
            {
                'nombre': 'Noretisterona + Etinilestradiol',
                'principio_activo': 'Noretisterona + Etinilestradiol',
                'presentacion': 'Comprimidos',
                'concentracion': '1/0.035 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03AA07'
            },
            {
                'nombre': 'Clomifeno',
                'principio_activo': 'Clomifeno citrato',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03GB02'
            },
            {
                'nombre': 'Letrozol',
                'principio_activo': 'Letrozol',
                'presentacion': 'Comprimidos',
                'concentracion': '2.5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L02BG04'
            },
            {
                'nombre': 'Tamoxifeno',
                'principio_activo': 'Tamoxifeno citrato',
                'presentacion': 'Comprimidos',
                'concentracion': '20 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L02BA01'
            },
            {
                'nombre': 'Raloxifeno',
                'principio_activo': 'Raloxifeno clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '60 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03XC01'
            },
            {
                'nombre': 'Estradiol',
                'principio_activo': 'Estradiol',
                'presentacion': 'Parche transdérmico',
                'concentracion': '50 mcg/24h',
                'via_administracion': 'Transdérmica',
                'codigo_atc': 'G03CA03'
            },
            {
                'nombre': 'Estradiol',
                'principio_activo': 'Estradiol',
                'presentacion': 'Comprimidos',
                'concentracion': '2 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03CA03'
            },
            {
                'nombre': 'Estradiol + Noretisterona',
                'principio_activo': 'Estradiol + Acetato de noretisterona',
                'presentacion': 'Comprimidos',
                'concentracion': '2/1 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03FA11'
            },
            {
                'nombre': 'Progesterona',
                'principio_activo': 'Progesterona micronizada',
                'presentacion': 'Cápsulas',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03DA04'
            },
            {
                'nombre': 'Progesterona',
                'principio_activo': 'Progesterona',
                'presentacion': 'Óvulos vaginales',
                'concentracion': '200 mg',
                'via_administracion': 'Vaginal',
                'codigo_atc': 'G03DA04'
            },
            {
                'nombre': 'Didrogesterona',
                'principio_activo': 'Didrogesterona',
                'presentacion': 'Comprimidos',
                'concentracion': '10 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03DB01'
            },
            {
                'nombre': 'Mifepristona',
                'principio_activo': 'Mifepristona',
                'presentacion': 'Comprimidos',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'G03XB01'
            },
            {
                'nombre': 'Misoprostol',
                'principio_activo': 'Misoprostol',
                'presentacion': 'Comprimidos',
                'concentracion': '200 mcg',
                'via_administracion': 'Oral/Sublingual',
                'codigo_atc': 'G02AD06'
            },
            {
                'nombre': 'Oxitocina',
                'principio_activo': 'Oxitocina',
                'presentacion': 'Ampolla',
                'concentracion': '10 UI/ml',
                'via_administracion': 'Intravenosa/Intramuscular',
                'codigo_atc': 'H01BB02'
            },
            {
                'nombre': 'Metilergometrina',
                'principio_activo': 'Metilergometrina maleato',
                'presentacion': 'Ampolla',
                'concentracion': '0.2 mg/ml',
                'via_administracion': 'Intramuscular/Intravenosa',
                'codigo_atc': 'G02AB03'
            },
            {
                'nombre': 'Dinoprostona',
                'principio_activo': 'Dinoprostona',
                'presentacion': 'Gel vaginal',
                'concentracion': '1 mg',
                'via_administracion': 'Vaginal',
                'codigo_atc': 'G02AD02'
            },
            {
                'nombre': 'Metronidazol',
                'principio_activo': 'Metronidazol',
                'presentacion': 'Óvulos vaginales',
                'concentracion': '500 mg',
                'via_administracion': 'Vaginal',
                'codigo_atc': 'G01AF01'
            },
            {
                'nombre': 'Clotrimazol',
                'principio_activo': 'Clotrimazol',
                'presentacion': 'Óvulos vaginales',
                'concentracion': '500 mg',
                'via_administracion': 'Vaginal',
                'codigo_atc': 'G01AF02'
            },
            {
                'nombre': 'Miconazol',
                'principio_activo': 'Miconazol nitrato',
                'presentacion': 'Óvulos vaginales',
                'concentracion': '200 mg',
                'via_administracion': 'Vaginal',
                'codigo_atc': 'G01AF05'
            },
            {
                'nombre': 'Fluconazol',
                'principio_activo': 'Fluconazol',
                'presentacion': 'Comprimidos',
                'concentracion': '150 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'J02AC01'
            },
            {
                'nombre': 'Ácido Tranexámico',
                'principio_activo': 'Ácido tranexámico',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'B02AA02'
            },
            
            # MEDICACIÓN ONCOLÓGICA
            {
                'nombre': 'Doxorrubicina',
                'principio_activo': 'Doxorrubicina clorhidrato',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01DB01'
            },
            {
                'nombre': 'Epirrubicina',
                'principio_activo': 'Epirrubicina clorhidrato',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01DB03'
            },
            {
                'nombre': 'Ciclofosfamida',
                'principio_activo': 'Ciclofosfamida',
                'presentacion': 'Vial',
                'concentracion': '1 g',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01AA01'
            },
            {
                'nombre': 'Ciclofosfamida',
                'principio_activo': 'Ciclofosfamida',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01AA01'
            },
            {
                'nombre': 'Metotrexato',
                'principio_activo': 'Metotrexato sódico',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa/Intramuscular',
                'codigo_atc': 'L01BA01'
            },
            {
                'nombre': 'Metotrexato',
                'principio_activo': 'Metotrexato',
                'presentacion': 'Comprimidos',
                'concentracion': '2.5 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01BA01'
            },
            {
                'nombre': '5-Fluorouracilo',
                'principio_activo': 'Fluorouracilo',
                'presentacion': 'Vial',
                'concentracion': '500 mg/10 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01BC02'
            },
            {
                'nombre': 'Cisplatino',
                'principio_activo': 'Cisplatino',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XA01'
            },
            {
                'nombre': 'Carboplatino',
                'principio_activo': 'Carboplatino',
                'presentacion': 'Vial',
                'concentracion': '150 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XA02'
            },
            {
                'nombre': 'Oxaliplatino',
                'principio_activo': 'Oxaliplatino',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XA03'
            },
            {
                'nombre': 'Paclitaxel',
                'principio_activo': 'Paclitaxel',
                'presentacion': 'Vial',
                'concentracion': '30 mg/5 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01CD01'
            },
            {
                'nombre': 'Docetaxel',
                'principio_activo': 'Docetaxel',
                'presentacion': 'Vial',
                'concentracion': '80 mg/2 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01CD02'
            },
            {
                'nombre': 'Vincristina',
                'principio_activo': 'Vincristina sulfato',
                'presentacion': 'Vial',
                'concentracion': '1 mg/ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01CA02'
            },
            {
                'nombre': 'Vinblastina',
                'principio_activo': 'Vinblastina sulfato',
                'presentacion': 'Vial',
                'concentracion': '10 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01CA01'
            },
            {
                'nombre': 'Etopósido',
                'principio_activo': 'Etopósido',
                'presentacion': 'Vial',
                'concentracion': '100 mg/5 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01CB01'
            },
            {
                'nombre': 'Etopósido',
                'principio_activo': 'Etopósido',
                'presentacion': 'Cápsulas',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01CB01'
            },
            {
                'nombre': 'Irinotecán',
                'principio_activo': 'Irinotecán clorhidrato',
                'presentacion': 'Vial',
                'concentracion': '100 mg/5 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XX19'
            },
            {
                'nombre': 'Topotecán',
                'principio_activo': 'Topotecán clorhidrato',
                'presentacion': 'Vial',
                'concentracion': '4 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XX17'
            },
            {
                'nombre': 'Gemcitabina',
                'principio_activo': 'Gemcitabina clorhidrato',
                'presentacion': 'Vial',
                'concentracion': '1 g',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01BC05'
            },
            {
                'nombre': 'Capecitabina',
                'principio_activo': 'Capecitabina',
                'presentacion': 'Comprimidos',
                'concentracion': '500 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01BC06'
            },
            {
                'nombre': 'Temozolomida',
                'principio_activo': 'Temozolomida',
                'presentacion': 'Cápsulas',
                'concentracion': '250 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01AX03'
            },
            {
                'nombre': 'Bendamustina',
                'principio_activo': 'Bendamustina clorhidrato',
                'presentacion': 'Vial',
                'concentracion': '100 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01AA09'
            },
            {
                'nombre': 'Ifosfamida',
                'principio_activo': 'Ifosfamida',
                'presentacion': 'Vial',
                'concentracion': '1 g',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01AA06'
            },
            {
                'nombre': 'Dacarbazina',
                'principio_activo': 'Dacarbazina',
                'presentacion': 'Vial',
                'concentracion': '200 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01AX04'
            },
            {
                'nombre': 'Procarbazina',
                'principio_activo': 'Procarbazina clorhidrato',
                'presentacion': 'Cápsulas',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XB01'
            },
            {
                'nombre': 'Bleomicina',
                'principio_activo': 'Bleomicina sulfato',
                'presentacion': 'Vial',
                'concentracion': '15 UI',
                'via_administracion': 'Intravenosa/Intramuscular',
                'codigo_atc': 'L01DC01'
            },
            {
                'nombre': 'Mitomicina',
                'principio_activo': 'Mitomicina C',
                'presentacion': 'Vial',
                'concentracion': '10 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01DC03'
            },
            {
                'nombre': 'Dactinomicina',
                'principio_activo': 'Dactinomicina',
                'presentacion': 'Vial',
                'concentracion': '0.5 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01DA01'
            },
            {
                'nombre': 'Imatinib',
                'principio_activo': 'Imatinib mesilato',
                'presentacion': 'Comprimidos',
                'concentracion': '400 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XE01'
            },
            {
                'nombre': 'Nilotinib',
                'principio_activo': 'Nilotinib clorhidrato monohidratado',
                'presentacion': 'Cápsulas',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XE08'
            },
            {
                'nombre': 'Dasatinib',
                'principio_activo': 'Dasatinib',
                'presentacion': 'Comprimidos',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XE06'
            },
            {
                'nombre': 'Sunitinib',
                'principio_activo': 'Sunitinib malato',
                'presentacion': 'Cápsulas',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XE04'
            },
            {
                'nombre': 'Sorafenib',
                'principio_activo': 'Sorafenib tosilato',
                'presentacion': 'Comprimidos',
                'concentracion': '200 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XE05'
            },
            {
                'nombre': 'Pazopanib',
                'principio_activo': 'Pazopanib clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '400 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01XE11'
            },
            {
                'nombre': 'Rituximab',
                'principio_activo': 'Rituximab',
                'presentacion': 'Vial',
                'concentracion': '100 mg/10 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XC02'
            },
            {
                'nombre': 'Trastuzumab',
                'principio_activo': 'Trastuzumab',
                'presentacion': 'Vial',
                'concentracion': '150 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XC03'
            },
            {
                'nombre': 'Bevacizumab',
                'principio_activo': 'Bevacizumab',
                'presentacion': 'Vial',
                'concentracion': '100 mg/4 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XC07'
            },
            {
                'nombre': 'Cetuximab',
                'principio_activo': 'Cetuximab',
                'presentacion': 'Vial',
                'concentracion': '100 mg/50 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XC06'
            },
            {
                'nombre': 'Pembrolizumab',
                'principio_activo': 'Pembrolizumab',
                'presentacion': 'Vial',
                'concentracion': '100 mg/4 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01FF02'
            },
            {
                'nombre': 'Nivolumab',
                'principio_activo': 'Nivolumab',
                'presentacion': 'Vial',
                'concentracion': '100 mg/10 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01FF07'
            },
            {
                'nombre': 'Atezolizumab',
                'principio_activo': 'Atezolizumab',
                'presentacion': 'Vial',
                'concentracion': '1200 mg/20 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01FF08'
            },
            {
                'nombre': 'Bortezomib',
                'principio_activo': 'Bortezomib',
                'presentacion': 'Vial',
                'concentracion': '3.5 mg',
                'via_administracion': 'Subcutánea/Intravenosa',
                'codigo_atc': 'L01XX32'
            },
            {
                'nombre': 'Carfilzomib',
                'principio_activo': 'Carfilzomib',
                'presentacion': 'Vial',
                'concentracion': '60 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01XX45'
            },
            {
                'nombre': 'Lenalidomida',
                'principio_activo': 'Lenalidomida',
                'presentacion': 'Cápsulas',
                'concentracion': '25 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L04AX04'
            },
            {
                'nombre': 'Pomalidomida',
                'principio_activo': 'Pomalidomida',
                'presentacion': 'Cápsulas',
                'concentracion': '4 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L04AX06'
            },
            {
                'nombre': 'Talidomida',
                'principio_activo': 'Talidomida',
                'presentacion': 'Cápsulas',
                'concentracion': '100 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L04AX02'
            },
            {
                'nombre': 'Fludarabina',
                'principio_activo': 'Fludarabina fosfato',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01BB05'
            },
            {
                'nombre': 'Cladribina',
                'principio_activo': 'Cladribina',
                'presentacion': 'Vial',
                'concentracion': '10 mg/10 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'L01BB04'
            },
            {
                'nombre': 'Citarabina',
                'principio_activo': 'Citarabina',
                'presentacion': 'Vial',
                'concentracion': '100 mg',
                'via_administracion': 'Intravenosa/Subcutánea',
                'codigo_atc': 'L01BC01'
            },
            {
                'nombre': 'Mercaptopurina',
                'principio_activo': 'Mercaptopurina',
                'presentacion': 'Comprimidos',
                'concentracion': '50 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01BB02'
            },
            {
                'nombre': 'Tioguanina',
                'principio_activo': 'Tioguanina',
                'presentacion': 'Comprimidos',
                'concentracion': '40 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01BB03'
            },
            {
                'nombre': 'Busulfán',
                'principio_activo': 'Busulfán',
                'presentacion': 'Comprimidos',
                'concentracion': '2 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01AB01'
            },
            {
                'nombre': 'Melfalán',
                'principio_activo': 'Melfalán clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '2 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01AA03'
            },
            {
                'nombre': 'Clorambucilo',
                'principio_activo': 'Clorambucilo',
                'presentacion': 'Comprimidos',
                'concentracion': '2 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'L01AA02'
            },
            {
                'nombre': 'L-Asparaginasa',
                'principio_activo': 'Asparaginasa',
                'presentacion': 'Vial',
                'concentracion': '10000 UI',
                'via_administracion': 'Intravenosa/Intramuscular',
                'codigo_atc': 'L01XX02'
            },
            {
                'nombre': 'Pegaspargasa',
                'principio_activo': 'Pegaspargasa',
                'presentacion': 'Vial',
                'concentracion': '3750 UI/5 ml',
                'via_administracion': 'Intramuscular/Intravenosa',
                'codigo_atc': 'L01XX24'
            },
            {
                'nombre': 'Interferón Alfa-2b',
                'principio_activo': 'Interferón alfa-2b',
                'presentacion': 'Vial',
                'concentracion': '3 millones UI',
                'via_administracion': 'Subcutánea/Intramuscular',
                'codigo_atc': 'L03AB05'
            },
            {
                'nombre': 'Peginterferón Alfa-2a',
                'principio_activo': 'Peginterferón alfa-2a',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '180 mcg/0.5 ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'L03AB11'
            },
            {
                'nombre': 'Filgrastim',
                'principio_activo': 'Filgrastim',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '300 mcg/0.5 ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'L03AA02'
            },
            {
                'nombre': 'Pegfilgrastim',
                'principio_activo': 'Pegfilgrastim',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '6 mg/0.6 ml',
                'via_administracion': 'Subcutánea',
                'codigo_atc': 'L03AA13'
            },
            {
                'nombre': 'Eritropoyetina',
                'principio_activo': 'Epoetina alfa',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '4000 UI/0.4 ml',
                'via_administracion': 'Subcutánea/Intravenosa',
                'codigo_atc': 'B03XA01'
            },
            {
                'nombre': 'Darbepoetina Alfa',
                'principio_activo': 'Darbepoetina alfa',
                'presentacion': 'Jeringa prellenada',
                'concentracion': '40 mcg/0.4 ml',
                'via_administracion': 'Subcutánea/Intravenosa',
                'codigo_atc': 'B03XA02'
            },
            {
                'nombre': 'Ondansetrón',
                'principio_activo': 'Ondansetrón clorhidrato',
                'presentacion': 'Comprimidos',
                'concentracion': '8 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A04AA01'
            },
            {
                'nombre': 'Ondansetrón',
                'principio_activo': 'Ondansetrón clorhidrato',
                'presentacion': 'Ampolla',
                'concentracion': '8 mg/4 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'A04AA01'
            },
            {
                'nombre': 'Granisetrón',
                'principio_activo': 'Granisetrón clorhidrato',
                'presentacion': 'Ampolla',
                'concentracion': '3 mg/3 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'A04AA02'
            },
            {
                'nombre': 'Palonosetrón',
                'principio_activo': 'Palonosetrón clorhidrato',
                'presentacion': 'Ampolla',
                'concentracion': '0.25 mg/5 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'A04AA05'
            },
            {
                'nombre': 'Aprepitant',
                'principio_activo': 'Aprepitant',
                'presentacion': 'Cápsulas',
                'concentracion': '125 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'A04AD12'
            },
            {
                'nombre': 'Fosaprepitant',
                'principio_activo': 'Fosaprepitant dimeglumina',
                'presentacion': 'Vial',
                'concentracion': '150 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'A04AD13'
            },
            {
                'nombre': 'Dexametasona',
                'principio_activo': 'Dexametasona',
                'presentacion': 'Comprimidos',
                'concentracion': '4 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'H02AB02'
            },
            {
                'nombre': 'Metilprednisolona',
                'principio_activo': 'Metilprednisolona',
                'presentacion': 'Vial',
                'concentracion': '500 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'H02AB04'
            },
            {
                'nombre': 'Allopurinol',
                'principio_activo': 'Allopurinol',
                'presentacion': 'Comprimidos',
                'concentracion': '300 mg',
                'via_administracion': 'Oral',
                'codigo_atc': 'M04AA01'
            },
            {
                'nombre': 'Mesna',
                'principio_activo': 'Mesna',
                'presentacion': 'Vial',
                'concentracion': '400 mg/4 ml',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'V03AF03'
            },
            {
                'nombre': 'Leucovorina',
                'principio_activo': 'Ácido folínico',
                'presentacion': 'Vial',
                'concentracion': '50 mg',
                'via_administracion': 'Intravenosa',
                'codigo_atc': 'V03AF03'
            },
        ]

        # Crear medicamentos
        self.stdout.write('Creando medicamentos...')
        medicamentos_creados = 0
        medicamentos_actualizados = 0
        
        for med_data in medicamentos:
            # Crear clave única basada en nombre + concentración + presentación
            nombre_completo = f"{med_data['nombre']} {med_data['concentracion']} {med_data['presentacion']}"
            
            medicamento, created = Medicamento.objects.update_or_create(
                nombre=nombre_completo,
                defaults={
                    'principio_activo': med_data['principio_activo'],
                    'presentacion': med_data['presentacion'],
                    'concentracion': med_data['concentracion'],
                    'via_administracion': med_data['via_administracion'],
                    'codigo_atc': med_data.get('codigo_atc', ''),
                    'activo': True
                }
            )
            if created:
                medicamentos_creados += 1
            else:
                medicamentos_actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Medicamentos: {medicamentos_creados} creados, {medicamentos_actualizados} actualizados'
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Proceso completado. Total: {len(medicamentos)} medicamentos disponibles.'
            )
        )

