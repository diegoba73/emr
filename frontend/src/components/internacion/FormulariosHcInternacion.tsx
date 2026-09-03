import React, { useCallback, useEffect, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  createHcResource,
  deleteHcResource,
  listHcResource,
  patchInternacionHcIngreso,
} from '../../services/internacion';
import type { InternacionCama, MedicacionHabitualInternacion, User } from '../../types';
import {
  canWriteHcMedico,
} from '../../utils/permissions';

interface IndicacionRow {
  id: number;
  fecha: string;
  hidratacion: string;
  oxigenoterapia: string;
  reposo: string;
  controles: string;
  precauciones: string;
  indicaciones: string;
  vigente: boolean;
  registrado_por_nombre?: string | null;
}

interface MedicacionRow {
  id: number;
  fecha: string;
  medicamento: string;
  dosis: string;
  via: string;
  frecuencia: string;
  horario: string;
  activa: boolean;
  observaciones: string;
  registrado_por_nombre?: string | null;
}

const formatFecha = (iso: string) => (iso ? new Date(iso).toLocaleString('es-AR') : '—');

interface FormulariosHcInternacionProps {
  internacionId: number;
  internacion: InternacionCama | null;
  currentUser: User | null;
  onInternacionUpdated: (data: InternacionCama) => void;
}

const FormulariosHcInternacion: React.FC<FormulariosHcInternacionProps> = ({
  internacionId,
  internacion,
  currentUser,
  onInternacionUpdated,
}) => {
  const writeMedico = canWriteHcMedico(currentUser);

  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [alergias, setAlergias] = useState('');
  const [tieneAlergias, setTieneAlergias] = useState<'' | 'si' | 'no'>('');
  const [anamnesis, setAnamnesis] = useState('');
  const [examen, setExamen] = useState('');
  const [motivo, setMotivo] = useState('');
  const [planEstudio, setPlanEstudio] = useState('');
  const [estadoCivil, setEstadoCivil] = useState('');
  const [familiarNombre, setFamiliarNombre] = useState('');
  const [familiarTelefono, setFamiliarTelefono] = useState('');
  const [habituales, setHabituales] = useState<MedicacionHabitualInternacion[]>([]);
  const [habForm, setHabForm] = useState({ medicamento: '', dosis_mg_dia: '' });

  const [indicaciones, setIndicaciones] = useState<IndicacionRow[]>([]);
  const [medicaciones, setMedicaciones] = useState<MedicacionRow[]>([]);

  const [indForm, setIndForm] = useState({
    hidratacion: '',
    oxigenoterapia: '',
    reposo: '',
    controles: '',
    precauciones: '',
    indicaciones: '',
  });
  const [medForm, setMedForm] = useState({
    medicamento: '',
    dosis: '',
    via: '',
    frecuencia: '',
    horario: '',
    observaciones: '',
  });

  useEffect(() => {
    setAlergias(internacion?.alergias || '');
    setTieneAlergias(
      internacion?.tiene_alergias === true ? 'si' : internacion?.tiene_alergias === false ? 'no' : '',
    );
    setAnamnesis(internacion?.anamnesis_ingreso || '');
    setExamen(internacion?.examen_fisico_ingreso || '');
    setMotivo(internacion?.motivo_ingreso || '');
    setPlanEstudio(internacion?.plan_estudio_tratamiento || '');
    const cab = internacion?.paciente_cabecera;
    setEstadoCivil(cab?.estado_civil || '');
    setFamiliarNombre(cab?.familiar_nombre || '');
    setFamiliarTelefono(cab?.familiar_telefono || '');
    setHabituales(internacion?.medicaciones_habituales || []);
  }, [internacion]);

  const loadAll = useCallback(async () => {
    setError(null);
    try {
      const [ind, med, hab] = await Promise.all([
        listHcResource<IndicacionRow>(internacionId, 'indicaciones-medicas'),
        listHcResource<MedicacionRow>(internacionId, 'medicaciones'),
        listHcResource<MedicacionHabitualInternacion>(internacionId, 'medicaciones-habituales'),
      ]);
      setIndicaciones(ind);
      setMedicaciones(med);
      setHabituales(hab);
    } catch {
      setError('No se pudieron cargar los formularios de internación.');
    }
  }, [internacionId]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const run = async (fn: () => Promise<void>) => {
    setSaving(true);
    setError(null);
    try {
      await fn();
    } catch {
      setError('No se pudo guardar. Revisá los permisos o los datos.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Ingreso e indicaciones médicas del episodio. Los registros diarios de enfermería y
        kinesiología se cargan únicamente en Revista de sala.
      </Typography>
      {internacion?.paciente_cabecera && (
        <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
          <Typography variant="subtitle2" gutterBottom>
            Cabecera de internación
          </Typography>
          <Typography variant="body2">
            {internacion.paciente_cabecera.apellido}, {internacion.paciente_cabecera.nombre}
            {' · DNI '}
            {internacion.paciente_cabecera.dni || '—'}
            {internacion.paciente_cabecera.edad != null
              ? ` · ${internacion.paciente_cabecera.edad} años`
              : ''}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            HC {internacion.paciente_cabecera.numero_internacion || internacion.numero_internacion || '—'}
            {' · '}
            {internacion.paciente_cabecera.sector || '—'} / {internacion.paciente_cabecera.cama || internacion.cama_nombre || '—'}
            {' · OS '}
            {internacion.paciente_cabecera.obra_social || '—'}
            {internacion.paciente_cabecera.numero_afiliado
              ? ` (${internacion.paciente_cabecera.numero_afiliado})`
              : ''}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Ingreso:{' '}
            {internacion.paciente_cabecera.fecha_ingreso
              ? new Date(internacion.paciente_cabecera.fecha_ingreso).toLocaleString('es-AR')
              : '—'}
            {' · Alta: '}
            {internacion.paciente_cabecera.fecha_alta
              ? new Date(internacion.paciente_cabecera.fecha_alta).toLocaleString('es-AR')
              : '—'}
          </Typography>
        </Box>
      )}
      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontWeight={700}>Médico — ingreso e indicaciones</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Stack spacing={1.5}>
            <TextField
              label="Estado civil"
              value={estadoCivil}
              onChange={(e) => setEstadoCivil(e.target.value)}
              disabled={!writeMedico}
            />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
              <TextField
                label="Familiar (nombre y apellido)"
                value={familiarNombre}
                onChange={(e) => setFamiliarNombre(e.target.value)}
                disabled={!writeMedico}
                fullWidth
              />
              <TextField
                label="Teléfono del familiar"
                value={familiarTelefono}
                onChange={(e) => setFamiliarTelefono(e.target.value)}
                disabled={!writeMedico}
                fullWidth
              />
            </Stack>
            <TextField
              label="Motivo de consulta / ingreso"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              multiline
              minRows={2}
              disabled={!writeMedico}
            />
            <FormControl>
              <FormLabel>Alergias</FormLabel>
              <RadioGroup
                row
                value={tieneAlergias}
                onChange={(e) => setTieneAlergias(e.target.value as 'si' | 'no')}
              >
                <FormControlLabel value="si" control={<Radio disabled={!writeMedico} />} label="Sí" />
                <FormControlLabel value="no" control={<Radio disabled={!writeMedico} />} label="No" />
              </RadioGroup>
            </FormControl>
            <TextField
              label="¿A qué?"
              value={alergias}
              onChange={(e) => setAlergias(e.target.value)}
              multiline
              minRows={2}
              disabled={!writeMedico || tieneAlergias === 'no'}
            />
            <TextField
              label="Enfermedad actual"
              value={anamnesis}
              onChange={(e) => setAnamnesis(e.target.value)}
              multiline
              minRows={3}
              disabled={!writeMedico}
            />
            <TextField
              label="Examen físico de ingreso"
              value={examen}
              onChange={(e) => setExamen(e.target.value)}
              multiline
              minRows={3}
              disabled={!writeMedico}
            />
            <TextField
              label="Plan de estudio / tratamiento"
              value={planEstudio}
              onChange={(e) => setPlanEstudio(e.target.value)}
              multiline
              minRows={2}
              disabled={!writeMedico}
            />
            <Typography variant="subtitle2">Medicación habitual (mg/día)</Typography>
            {habituales.map((row) => (
              <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
                <Typography variant="body2">
                  {row.medicamento} {row.dosis_mg_dia ? `${row.dosis_mg_dia} mg/día` : ''}
                </Typography>
                {writeMedico && (
                  <Button
                    size="small"
                    onClick={() =>
                      void run(async () => {
                        await deleteHcResource(internacionId, 'medicaciones-habituales', row.id);
                        await loadAll();
                      })
                    }
                  >
                    Quitar
                  </Button>
                )}
              </Box>
            ))}
            {!habituales.length && internacion?.medicacion_habitual && (
              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                Registro previo: {internacion.medicacion_habitual}
              </Typography>
            )}
            {writeMedico && (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <TextField
                  label="Medicamento"
                  value={habForm.medicamento}
                  onChange={(e) => setHabForm({ ...habForm, medicamento: e.target.value })}
                  fullWidth
                />
                <TextField
                  label="mg/día"
                  value={habForm.dosis_mg_dia}
                  onChange={(e) => setHabForm({ ...habForm, dosis_mg_dia: e.target.value })}
                />
                <Button
                  variant="outlined"
                  disabled={saving || !habForm.medicamento.trim()}
                  onClick={() =>
                    void run(async () => {
                      await createHcResource(internacionId, 'medicaciones-habituales', habForm);
                      setHabForm({ medicamento: '', dosis_mg_dia: '' });
                      await loadAll();
                    })
                  }
                >
                  Agregar
                </Button>
              </Stack>
            )}
            {writeMedico && (
              <Button
                variant="contained"
                disabled={saving}
                onClick={() =>
                  void run(async () => {
                    const updated = await patchInternacionHcIngreso(internacionId, {
                      alergias: tieneAlergias === 'no' ? '' : alergias,
                      tiene_alergias: tieneAlergias === 'si' ? true : tieneAlergias === 'no' ? false : null,
                      anamnesis_ingreso: anamnesis,
                      examen_fisico_ingreso: examen,
                      plan_estudio_tratamiento: planEstudio,
                      motivo_ingreso: motivo,
                      estado_civil: estadoCivil,
                      familiar_nombre: familiarNombre,
                      familiar_telefono: familiarTelefono,
                    });
                    onInternacionUpdated(updated);
                  })
                }
              >
                Guardar datos de ingreso
              </Button>
            )}

            <Typography variant="subtitle2" sx={{ pt: 1 }}>
              Indicaciones médicas
            </Typography>
            {indicaciones.map((row) => (
              <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatFecha(row.fecha)} · {row.registrado_por_nombre || '—'}
                  {row.vigente ? '' : ' · no vigente'}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {[row.hidratacion && `Hidratación: ${row.hidratacion}`,
                    row.oxigenoterapia && `O2: ${row.oxigenoterapia}`,
                    row.reposo && `Reposo: ${row.reposo}`,
                    row.controles && `Controles: ${row.controles}`,
                    row.precauciones,
                    row.indicaciones,
                  ]
                    .filter(Boolean)
                    .join('\n')}
                </Typography>
              </Box>
            ))}
            {writeMedico && (
              <Stack spacing={1}>
                <TextField
                  label="Hidratación"
                  value={indForm.hidratacion}
                  onChange={(e) => setIndForm({ ...indForm, hidratacion: e.target.value })}
                />
                <TextField
                  label="Oxigenoterapia"
                  value={indForm.oxigenoterapia}
                  onChange={(e) => setIndForm({ ...indForm, oxigenoterapia: e.target.value })}
                />
                <TextField
                  label="Reposo"
                  value={indForm.reposo}
                  onChange={(e) => setIndForm({ ...indForm, reposo: e.target.value })}
                />
                <TextField
                  label="Controles (TA, FC, glucemia…)"
                  value={indForm.controles}
                  onChange={(e) => setIndForm({ ...indForm, controles: e.target.value })}
                />
                <TextField
                  label="Precauciones"
                  value={indForm.precauciones}
                  onChange={(e) => setIndForm({ ...indForm, precauciones: e.target.value })}
                  multiline
                />
                <TextField
                  label="Indicaciones"
                  value={indForm.indicaciones}
                  onChange={(e) => setIndForm({ ...indForm, indicaciones: e.target.value })}
                  multiline
                  minRows={2}
                />
                <Button
                  variant="outlined"
                  disabled={saving}
                  onClick={() =>
                    void run(async () => {
                      await createHcResource(internacionId, 'indicaciones-medicas', indForm);
                      setIndForm({
                        hidratacion: '',
                        oxigenoterapia: '',
                        reposo: '',
                        controles: '',
                        precauciones: '',
                        indicaciones: '',
                      });
                      await loadAll();
                    })
                  }
                >
                  Agregar indicación
                </Button>
              </Stack>
            )}

            <Typography variant="subtitle2" sx={{ pt: 1 }}>
              Medicación de internación
            </Typography>
            {medicaciones.map((row) => (
              <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
                <Typography variant="body2" fontWeight={600}>
                  {row.medicamento} {row.dosis} {row.via} {row.frecuencia}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatFecha(row.fecha)} · {row.horario} · {row.activa ? 'activa' : 'suspendida'}
                </Typography>
              </Box>
            ))}
            {writeMedico && (
              <Stack spacing={1}>
                <TextField
                  label="Medicamento"
                  value={medForm.medicamento}
                  onChange={(e) => setMedForm({ ...medForm, medicamento: e.target.value })}
                  required
                />
                <Stack direction="row" spacing={1}>
                  <TextField
                    label="Dosis"
                    value={medForm.dosis}
                    onChange={(e) => setMedForm({ ...medForm, dosis: e.target.value })}
                  />
                  <TextField
                    label="Vía"
                    value={medForm.via}
                    onChange={(e) => setMedForm({ ...medForm, via: e.target.value })}
                  />
                </Stack>
                <Stack direction="row" spacing={1}>
                  <TextField
                    label="Frecuencia"
                    value={medForm.frecuencia}
                    onChange={(e) => setMedForm({ ...medForm, frecuencia: e.target.value })}
                  />
                  <TextField
                    label="Horario"
                    value={medForm.horario}
                    onChange={(e) => setMedForm({ ...medForm, horario: e.target.value })}
                  />
                </Stack>
                <TextField
                  label="Observaciones"
                  value={medForm.observaciones}
                  onChange={(e) => setMedForm({ ...medForm, observaciones: e.target.value })}
                />
                <Button
                  variant="outlined"
                  disabled={saving || !medForm.medicamento.trim()}
                  onClick={() =>
                    void run(async () => {
                      await createHcResource(internacionId, 'medicaciones', medForm);
                      setMedForm({
                        medicamento: '',
                        dosis: '',
                        via: '',
                        frecuencia: '',
                        horario: '',
                        observaciones: '',
                      });
                      await loadAll();
                    })
                  }
                >
                  Agregar medicación
                </Button>
              </Stack>
            )}
          </Stack>
        </AccordionDetails>
      </Accordion>
    </Stack>
  );
};

export default FormulariosHcInternacion;
