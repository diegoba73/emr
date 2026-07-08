from medicos.icpl_cehta_csv import (
    canonical_especialidad_nombre,
    dedupe_icpl_medicos,
    load_icpl_medicos_from_csv,
    parse_icpl_medico_row,
)
from django.test import SimpleTestCase


class IcplCehtaMedicoCsvTests(SimpleTestCase):
    def test_parse_row(self):
        row = {
            "import_id": "MED-012",
            "institucion_codigo": "ICPL",
            "apellido": "Ingaramo",
            "nombres": "Roberto Antonio",
            "especialidad_principal": "Cardiología",
            "matricula_profesional": "",
            "activo_sugerido": "1",
        }
        parsed = parse_icpl_medico_row(row, line_no=2)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.apellido, "Ingaramo")
        self.assertEqual(parsed.especialidad_principal, "Cardiología")

    def test_canonical_especialidad_aliases(self):
        self.assertEqual(canonical_especialidad_nombre("Clínica médica"), "Clínica médica")
        self.assertEqual(
            canonical_especialidad_nombre("Cardiología intervencionista"),
            "Cardiología",
        )
        self.assertIsNone(canonical_especialidad_nombre("No verificada"))

    def test_dedupe_same_doctor_two_institutions(self):
        cehta = parse_icpl_medico_row(
            {
                "import_id": "MED-001",
                "institucion_codigo": "CEHTA",
                "apellido": "Ingaramo",
                "nombres": "Roberto Antonio",
                "especialidad_principal": "Cardiología",
                "activo_sugerido": "1",
            },
            line_no=2,
        )
        icpl = parse_icpl_medico_row(
            {
                "import_id": "MED-012",
                "institucion_codigo": "ICPL",
                "apellido": "Ingaramo",
                "nombres": "Roberto Antonio",
                "especialidad_principal": "Cardiología",
                "horario_consultorio": "Viernes 09:15 a 12:00",
                "activo_sugerido": "1",
            },
            line_no=13,
        )
        assert cehta is not None and icpl is not None
        medicos, warnings = dedupe_icpl_medicos([cehta, icpl])
        self.assertEqual(len(medicos), 1)
        merged = next(iter(medicos.values()))
        self.assertEqual(merged.institucion_codigo, "CEHTA/ICPL")
        self.assertIn("Viernes", merged.horario_consultorio)
        self.assertEqual(warnings, [])

    def test_load_fixture(self):
        from pathlib import Path
        import tempfile

        fixture = (
            "import_id,apellido,nombres,especialidad_principal,institucion_codigo,activo_sugerido\n"
            "MED-001,Ingaramo,Roberto Antonio,Cardiología,CEHTA,1\n"
            "MED-012,Ingaramo,Roberto Antonio,Cardiología,ICPL,1\n"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".csv", delete=False) as handle:
            handle.write(fixture)
            path = Path(handle.name)

        medicos, stats = load_icpl_medicos_from_csv(path)
        path.unlink(missing_ok=True)
        self.assertEqual(stats.rows_parsed, 2)
        self.assertEqual(stats.unique_medicos, 1)
