from datetime import date

from django.test import SimpleTestCase

from pacientes.icpl_csv import (
    dedupe_icpl_patients,
    load_icpl_patients_from_csv,
    parse_icpl_csv_row,
)


class IcplCsvParserTests(SimpleTestCase):
    def test_parse_row_with_comma_name(self):
        row = [
            "14044",
            "19:18",
            "22/5/2020",
            "RAMIREZ, FLORENTINO",
            "2945694671-2945404573",
            "10571475",
            "PAMI",
            "150823406404-00",
            "5/4/1953",
            "67",
            "",
            "ESTENOSIS AORTICA SEVERA",
            "RAMIREZ ABEL (HIJO)",
            "BARTOLOME MITRE 18.RIO SENGUER",
        ]
        parsed = parse_icpl_csv_row(row, line_no=4)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.dni, "10571475")
        self.assertEqual(parsed.apellido, "Ramirez")
        self.assertEqual(parsed.nombre, "Florentino")
        self.assertEqual(parsed.fecha_nacimiento, date(1953, 4, 5))
        self.assertEqual(parsed.telefono, "2945694671")
        self.assertEqual(parsed.obra_social, "PAMI")
        self.assertEqual(parsed.numero_afiliado, "150823406404-00")

    def test_parse_row_without_comma(self):
        row = ["", "", "1/6/2020", "NIEVA GABRIEL", "154696046", "11916948", "PAMI", "", "24/4/1958", "62", "M"]
        parsed = parse_icpl_csv_row(row, line_no=10)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.apellido, "Nieva")
        self.assertEqual(parsed.nombre, "Gabriel")
        self.assertEqual(parsed.sexo, "M")

    def test_parse_birth_month_year(self):
        row = ["", "", "", "BESADA SANTIAGO", "", "93496285", "PAMI", "", "jul-52", "67", "M"]
        parsed = parse_icpl_csv_row(row, line_no=49)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.fecha_nacimiento, date(1952, 7, 1))

    def test_skip_month_header(self):
        row = ["MAYO"] + [""] * 10
        self.assertIsNone(parse_icpl_csv_row(row, line_no=3))

    def test_dedupe_keeps_latest_admission(self):
        older = parse_icpl_csv_row(
            [
                "1",
                "",
                "1/1/2020",
                "PEREZ, JUAN",
                "2804000000",
                "12345678",
                "PAMI",
                "111",
                "1/1/1980",
                "40",
                "M",
                "",
                "",
                "DIR VIEJA",
            ],
            line_no=1,
        )
        newer = parse_icpl_csv_row(
            [
                "2",
                "",
                "1/1/2025",
                "PEREZ, JUAN",
                "2804111111",
                "12345678",
                "SEROS",
                "222",
                "1/1/1980",
                "45",
                "M",
                "",
                "",
                "DIR NUEVA",
            ],
            line_no=2,
        )
        assert older is not None and newer is not None
        patients, warnings = dedupe_icpl_patients([older, newer])
        self.assertEqual(len(patients), 1)
        merged = patients["12345678"]
        self.assertEqual(merged.direccion, "DIR NUEVA")
        self.assertEqual(merged.telefono, "2804111111")
        self.assertEqual(merged.obra_social, "SEROS")
        self.assertEqual(warnings, [])

    def test_dedupe_prefers_newer_obra_social(self):
        older = parse_icpl_csv_row(
            ["", "", "1/1/2020", "LOPEZ, ANA", "", "87654321", "PAMI", "111", "1/1/1990", "", "F"],
            line_no=1,
        )
        newer = parse_icpl_csv_row(
            ["", "", "1/1/2025", "LOPEZ, ANA", "", "87654321", "OSDE", "222", "1/1/1990", "", "F"],
            line_no=2,
        )
        assert older is not None and newer is not None
        patients, _ = dedupe_icpl_patients([older, newer])
        self.assertEqual(patients["87654321"].obra_social, "OSDE")
        self.assertEqual(patients["87654321"].numero_afiliado, "222")


class IcplCsvFileTests(SimpleTestCase):
    def test_load_sample_fixture(self):
        fixture = (
            "N° HC;HORA ;FECHA;APELLIDO Y NOMBRE;TELÉFONO;DNI;OBRA SOCIAL;N° DE AFILIADO;FECHA DE NAC.;EDAD;SEXO\n"
            "MAYO;;;;;;;;;;;;;;;;;\n"
            "14044;19:18;22/5/2020;RAMIREZ, FLORENTINO;2945694671;10571475;PAMI;150823406404-00;5/4/1953;67;\n"
            "14048;13:50;25/5/2020;REINOSO,GORGONIO NICOLAS;2804677270;3456018;PAMI;0-10093497609;9/9/1929;90;\n"
        )
        from pathlib import Path
        import tempfile

        with tempfile.NamedTemporaryFile("w", encoding="latin-1", suffix=".csv", delete=False) as handle:
            handle.write(fixture)
            path = Path(handle.name)

        patients, stats = load_icpl_patients_from_csv(path)
        path.unlink(missing_ok=True)

        self.assertEqual(stats.rows_parsed, 2)
        self.assertEqual(stats.unique_patients, 2)
        self.assertIn("10571475", patients)
        self.assertEqual(patients["3456018"].nombre, "Gorgonio Nicolas")
