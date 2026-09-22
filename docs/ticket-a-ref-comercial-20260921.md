# Ticket A — REF comercial en inventario (2026-09-21)

## Entrega

Campo `InsumoLab.ref_comercial` (opcional, blank, indexado, **sin** unique global).

### Diff (archivos)

| Archivo | Cambio |
|---------|--------|
| `laboratorio/models_inventario.py` | campo `ref_comercial` |
| `laboratorio/migrations/0050_insumo_ref_comercial.py` | AddField no destructivo (tras `0049_modo_entrada_calculado`) |
| `laboratorio/serializers_inventario.py` | expone el campo |
| `laboratorio/views_inventario.py` | search incluye `ref_comercial` |
| `frontend/.../InventarioPage.tsx` | form + columna REF |
| `frontend/src/services/limsApi.ts` | tipo TS |
| `docs_synesis/reglas/inventario-reactivos.md` | documentación |
| `laboratorio/tests/test_inventario_reactivos.py` | `TestInsumoRefComercial` |

**No tocado:** QC, `ConsumoInsumoExamen`, CRE/GLU Pharmacorp, carga/validar/liberar.

### Migración

- Dependencia: `0049_modo_entrada_calculado`
- Solo `AddField` con `default=""` / `blank=True`
- Compatible con filas existentes (CRE/GLU quedan con REF vacía)
- Reversión: `migrate laboratorio 0049`

### Por qué no unique global

W216 / posibles presentaciones duplicadas o SKU distintos con misma REF de fabricante deben poder coexistir. Unicidad se puede imponer después por política de carga (Ticket B), no en schema.

### Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Aplicar migrate en BD prod sin backup | Solo dev en esta etapa; prod requiere auth + backup |
| Confundir `codigo` con REF en UI | Labels “Código” vs “REF comercial” |
| Ticket B cree consumos | Prohibido hasta auth |

### Cómo aplicar en desarrollo

```bash
docker compose exec -T backend python manage.py migrate laboratorio 0050
docker compose exec -T backend python manage.py test laboratorio.tests.test_inventario_reactivos.TestInsumoRefComercial laboratorio.tests.test_qc_gate.TestQcGateEquipo --keepdb -v1
```
No aplicar a datos reales de producción sin revisión.
