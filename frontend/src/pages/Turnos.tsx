import React, { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Calendar as BigCalendarBase } from 'react-big-calendar';
import { localizer } from '../utils/calendarLocalizer';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Turno, Medico } from '../types';
import { apiService } from '../services/api';
import { useData } from '../contexts/DataContext';
import TurnoDrawer from '../components/TurnoDrawer';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';
import {
  Box,
  Typography,
  Button,
  TextField,
  Autocomplete,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
	Tooltip,
	Alert,
} from '@mui/material';
import { Add, Clear, FilterList, Close } from '@mui/icons-material';
import './Turnos.css';
import {
	extractSearchWords,
	medicoMatchesSearch,
	pacienteMatchesSearch,
} from '../utils/search';
import { isSelectableSlotAction } from '../utils/calendarSlotSelection';
import {
	canCreateTurno,
	canEditTurno,
	canViewTurnosAgenda,
	isAgendaReadOnlyRole,
} from '../utils/turnoPermissions';
import { isTurnoEstudio } from '../utils/recursosEstudio';
import {
	formatTurnoCalendarTitle,
	getTurnoAgendaKind,
	getTurnoKindMeta,
	TURNO_KIND_META,
	type TurnoAgendaKind,
} from '../utils/turnoKind';
import {
	getTurnoEstadoColor,
	TURNO_ESTADOS_CALENDARIO,
} from '../utils/turnoEstadoColors';
import { canAsignarTurnoEstudio } from '../modules/estudios/permissions';
import { getEstudioComplementario } from '../services/estudiosComplementariosApi';
import { AGENDAR_ESTUDIO_QUERY } from '../utils/agendarEstudioNavigation';
import type { EstudioComplementario } from '../types/estudios';
// Los tipos locales de `react-big-calendar` en este proyecto no incluyen props
// como `min/max/scrollToTime` (aunque la librería sí las soporta). Casteamos el
// componente para mantener comportamiento sin ensuciar el resto del archivo.
const BigCalendar = BigCalendarBase as any;

/** Mismo día local + misma hora de inicio (0–23) — agrupa turnos “a la misma hora”. */
function turnoHourBucketKey(start: Date): string {
	return `${start.getFullYear()}-${start.getMonth()}-${start.getDate()}-${start.getHours()}`;
}

type TurnosCalendarOverflowResource = {
	isOverflow: true;
	extraCount: number;
	goTo: Date;
};

function isOverflowResource(
	r: Turno | TurnosCalendarOverflowResource
): r is TurnosCalendarOverflowResource {
	return (r as TurnosCalendarOverflowResource).isOverflow === true;
}

type CalendarEvent = {
	id: number | string;
	title: string;
	start: Date;
	end: Date;
	resource: Turno | TurnosCalendarOverflowResource;
};

function thirtyMinSlotKey(d: Date): string {
	return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}-${d.getHours()}-${d.getMinutes()}`;
}

/** Slots de 30 min (clave local) en los que hay al menos un turno — para mostrar franja punteada. */
function buildSlotKeysConTurno(events: CalendarEvent[]): Set<string> {
	const s = new Set<string>();
	for (const e of events) {
		const endMs = e.end.getTime();
		const t0 = new Date(e.start);
		t0.setSeconds(0, 0);
		const m = t0.getMinutes() % 30;
		t0.setMinutes(t0.getMinutes() - m, 0, 0);
		let t = t0.getTime();
		while (t < endMs) {
			s.add(thirtyMinSlotKey(new Date(t)));
			t += 30 * 60 * 1000;
		}
	}
	return s;
}

/**
 * Solo vista **semana**: misma hora de inicio (0–23).
 * - 1 turno: se muestra el turno.
 * - 2 o más: un solo bloque +N (N = total) y la franja; al clic +N se abre el día a esa hora.
 */
function buildWeekBucketCappedEvents(
	events: CalendarEvent[]
): CalendarEvent[] {
	const by = new Map<string, CalendarEvent[]>();
	for (const e of events) {
		const k = turnoHourBucketKey(e.start);
		if (!by.has(k)) by.set(k, []);
		by.get(k)!.push(e);
	}
	const out: CalendarEvent[] = [];
	let synth = 0;
	by.forEach((list, k) => {
		if (list.length === 0) {
			return;
		}
		if (list.length === 1) {
			out.push(list[0]);
			return;
		}
		const sorted = [...list].sort((a, b) => a.start.getTime() - b.start.getTime());
		const total = sorted.length;
		const tMin = new Date(Math.min(...list.map((ev) => ev.start.getTime())));
		const tMax = new Date(Math.max(...list.map((ev) => ev.end.getTime())));
		const goTo = new Date(
			tMin.getFullYear(),
			tMin.getMonth(),
			tMin.getDate(),
			tMin.getHours(),
			tMin.getMinutes(),
			0,
			0
		);
		out.push({
			id: `__overflow__${k}-${synth++}`,
			title: `+${total}`,
			start: tMin,
			end: tMax,
			resource: {
				isOverflow: true,
				extraCount: total,
				goTo,
			},
		});
	});
	return out;
}

const Turnos: React.FC = () => {
	const { 
		turnos, 
		medicos, 
		loading: dataLoading, 
		currentUser, 
		refreshTurnos,
	} = useData();
	const [showModal, setShowModal] = useState(false);
	/** Evita reemplazar toda la página al refrescar catálogos en segundo plano (p. ej. al abrir el modal). */
	const [hasLoadedOnce, setHasLoadedOnce] = useState(false);
	useEffect(() => {
		if (
			!dataLoading.turnos &&
			!dataLoading.pacientes &&
			!dataLoading.medicos &&
			!dataLoading.especialidades &&
			!dataLoading.centrosFisicos &&
			!dataLoading.tiposAtencion
		) {
			setHasLoadedOnce(true);
		}
	}, [
		dataLoading.turnos,
		dataLoading.pacientes,
		dataLoading.medicos,
		dataLoading.especialidades,
		dataLoading.centrosFisicos,
		dataLoading.tiposAtencion,
	]);
	const [editingTurno, setEditingTurno] = useState<Turno | null>(null);
	const [filterEstado, setFilterEstado] = useState<string>('');
	const [filterPaciente, setFilterPaciente] = useState<string>('');
	const [filterMedico, setFilterMedico] = useState<string>('');
	const [filterTipoRecurso, setFilterTipoRecurso] = useState<string>('');
	const [filterAgendaKind, setFilterAgendaKind] = useState<'all' | TurnoAgendaKind>('all');
	const [medicoInputValue, setMedicoInputValue] = useState<string>('');
	const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
	const [searchingMedicos, setSearchingMedicos] = useState(false);
	const medicoInputReason = useRef<'input' | 'selection' | 'clear'>('input');
	
	// Estados para el calendario
	const [currentView, setCurrentView] = useState<'month' | 'week' | 'day'>('week');
	const [currentDate, setCurrentDate] = useState(new Date());
	/** Tras clic en +N (vista semana): scroll a esta hora en vista día; se limpia a ~2 s */
	const [forcedScrollToTime, setForcedScrollToTime] = useState<Date | null>(null);
	const [selectedDateTime, setSelectedDateTime] = useState<Date | null>(null);
	const [searchParams, setSearchParams] = useSearchParams();
	const [estudioAgendaPendiente, setEstudioAgendaPendiente] = useState<EstudioComplementario | null>(null);

	const userCanCreateTurno = useMemo(() => canCreateTurno(currentUser), [currentUser]);
	const userCanAgendarEstudio = useMemo(() => canAsignarTurnoEstudio(currentUser), [currentUser]);
	const enModoAgendarEstudio = Boolean(estudioAgendaPendiente && userCanAgendarEstudio);
	const puedeAgendarEnCalendario = userCanCreateTurno || enModoAgendarEstudio;
	const agendaReadOnly = useMemo(() => isAgendaReadOnlyRole(currentUser), [currentUser]);
	const puedeVerAgenda = useMemo(() => canViewTurnosAgenda(currentUser), [currentUser]);

	const clearEstudioAgendaPendiente = useCallback(() => {
		setEstudioAgendaPendiente(null);
		if (searchParams.has(AGENDAR_ESTUDIO_QUERY)) {
			const next = new URLSearchParams(searchParams);
			next.delete(AGENDAR_ESTUDIO_QUERY);
			setSearchParams(next, { replace: true });
		}
	}, [searchParams, setSearchParams]);

	useEffect(() => {
		const raw = searchParams.get(AGENDAR_ESTUDIO_QUERY);
		if (!raw) {
			setEstudioAgendaPendiente(null);
			return;
		}
		const id = Number(raw);
		if (!Number.isFinite(id) || id <= 0) return;
		let cancelled = false;
		(async () => {
			try {
				const est = await getEstudioComplementario(id);
				if (!cancelled) {
					setEstudioAgendaPendiente(est);
					setFilterAgendaKind('estudio');
				}
			} catch {
				if (!cancelled) setEstudioAgendaPendiente(null);
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [searchParams]);

	// Ventana horaria visible:
	// clickeable y no haya mismatch perceptivo entre pixel clickeado y slot.
	// (Default de react-big-calendar es 00:00-23:59 => cada slot ~20px => imposible acertar).
	const calendarMinTime = useMemo(() => {
		const d = new Date();
		d.setHours(7, 0, 0, 0);
		return d;
	}, []);
	const calendarMaxTime = useMemo(() => {
		const d = new Date();
		d.setHours(21, 0, 0, 0);
		return d;
	}, []);
	const calendarScrollToTime = useMemo(() => {
		const d = new Date();
		d.setHours(8, 0, 0, 0);
		return d;
	}, []);

	useEffect(() => {
		if (!forcedScrollToTime) return;
		const t = window.setTimeout(() => setForcedScrollToTime(null), 2000);
		return () => window.clearTimeout(t);
	}, [forcedScrollToTime]);
	
	// Estado para el drawer de atención (separado del modal para evitar resets)
	const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);

	const mergeUniqueById = <T extends { id?: number | string }>(...lists: Array<T[] | undefined>) => {
		const map = new Map<number | string, T>();
		lists.forEach(list => {
			(list || []).forEach(item => {
				if (item && item.id !== undefined && !map.has(item.id)) {
					map.set(item.id, item);
				}
			});
		});
		return Array.from(map.values());
	};

	const medicosBase = useMemo(() => mergeUniqueById(medicos), [medicos]);

	useEffect(() => {
		setMedicoOptions(medicosBase);
	}, [medicosBase]);

	const pacienteSearchWords = useMemo(() => extractSearchWords(filterPaciente), [filterPaciente]);

	useEffect(() => {
		if (medicoInputReason.current !== 'input') {
			medicoInputReason.current = 'input';
			return;
		}

		const query = medicoInputValue.trim();
		if (query.length < 2) {
			setMedicoOptions(medicosBase);
			setSearchingMedicos(false);
			return;
		}

		// Debounce: esperar 300ms después de que el usuario deje de escribir
		const timeoutId = setTimeout(() => {
			let active = true;
			setSearchingMedicos(true);

			apiService.buscarMedicos(query)
				.then(results => {
					if (!active) return;
					// Los resultados ya vienen ordenados del backend
					setMedicoOptions(mergeUniqueById(results, medicosBase));
				})
				.catch(() => {
					if (active) {
						setMedicoOptions(medicosBase);
					}
				})
				.finally(() => {
					if (active) setSearchingMedicos(false);
				});
		}, 300); // 300ms de debounce para búsquedas más eficientes

		return () => {
			clearTimeout(timeoutId);
		};
	}, [medicoInputValue, medicosBase]);

	const medicoSeleccionado = useMemo(() => {
		if (!filterMedico) return null;
		const id = Number(filterMedico);
		return medicosBase.find(m => m.id === id) || null;
	}, [filterMedico, medicosBase]);


	const filteredTurnos = turnos.filter(turno => {
		// Filtro por estado
		const estadoMatch = !filterEstado || turno.estado === filterEstado;
		
		// Filtro por paciente
		const pacienteMatch = pacienteSearchWords.length === 0 ||
			(turno.paciente ? pacienteMatchesSearch(turno.paciente, pacienteSearchWords) : false);
		
		// Filtro por médico: turnos de estudio en sala no tienen médico asignado al turno
		const medicoMatch = !filterMedico ||
			(turno.medico && turno.medico.id === Number(filterMedico)) ||
			(isTurnoEstudio(turno) &&
				turno.estudio_complementario?.medico_solicitante_id === Number(filterMedico)) ||
			(isTurnoEstudio(turno) && !turno.medico);

		const tipoMatch = !filterTipoRecurso ||
			(turno.recurso && turno.recurso.tipo_recurso === filterTipoRecurso);

		const agendaKindMatch =
			filterAgendaKind === 'all' || getTurnoAgendaKind(turno) === filterAgendaKind;
		
		return estadoMatch && pacienteMatch && medicoMatch && tipoMatch && agendaKindMatch;
	});

	// Mapear turnos a eventos del calendario
	const calendarEvents = useMemo((): CalendarEvent[] => {
		return filteredTurnos.map(turno => {
			const title = formatTurnoCalendarTitle(turno);

			return {
				id: turno.id,
				title,
				start: new Date(turno.fecha_hora_inicio),
				end: new Date(turno.fecha_hora_fin || new Date(turno.fecha_hora_inicio).getTime() + 60 * 60 * 1000),
				resource: turno,
			};
		});
	}, [filteredTurnos]);

	const slotKeysConTurno = useMemo(
		() => buildSlotKeysConTurno(calendarEvents),
		[calendarEvents]
	);

	const displayCalendarEvents = useMemo((): CalendarEvent[] => {
		if (currentView === 'month') {
			return calendarEvents;
		}
		/* Día: todos los turnos visibles y clickeables para editar (no +N). Semana: colapso +N. */
		if (currentView === 'day') {
			return calendarEvents;
		}
		return buildWeekBucketCappedEvents(calendarEvents);
	}, [calendarEvents, currentView]);

	// Abrir el modal con una fecha/hora específica. Punto único de entrada para
	// "click en calendario → nuevo turno", independientemente del camino (slot wrapper,
	// onSelectSlot por drag, o Month view).
	const openNewTurnoAt = useCallback((when: Date) => {
		if (enModoAgendarEstudio && estudioAgendaPendiente) {
			setSelectedDateTime(new Date(when.getTime()));
			setEditingTurno(null);
			setShowModal(true);
			return;
		}
		if (!canCreateTurno(currentUser)) return;
		setSelectedDateTime(new Date(when.getTime()));
		setEditingTurno(null);
		setShowModal(true);
	}, [currentUser, enModoAgendarEstudio, estudioAgendaPendiente]);

	// `onSelectSlot` de react-big-calendar calcula el slot por pixel, lo cual es
	// frágil (depende de `pageYOffset`, containers con overflow, CSS, etc.).
	// Para clicks simples en day/week ya tenemos `TimeSlotWrapper` que usa la
	// Date exacta del slot. Aquí sólo procesamos:
	//   - 'select' (drag-to-select en day/week): usa el inicio del rango.
	//   - 'click' en view month: la hora no tiene sentido, usamos la fecha.
	const handleSelectSlot = (slotInfo: { start: Date; end: Date; action: string; slots?: Date[] }) => {
		if (!puedeAgendarEnCalendario) return;
		if (!isSelectableSlotAction(slotInfo.action)) return;
		// En day/week los clicks los maneja TimeSlotWrapper (hora exacta).
		if (currentView !== 'month' && slotInfo.action === 'click') return;
		openNewTurnoAt(slotInfo.start);
	};

	const formatHoraCorta = (d: Date) =>
		d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });

	/**
	 * En semana y día, capa encima de los eventos: franja punteada solo en slots
	 * con al menos un turno, para agendar sin quedar tapada.
	 */
	const turnoEventContainerWrapper = useMemo(() => {
		return function TurnosEventContainerWrapper({
			children,
			slotMetrics,
		}: {
			children: React.ReactNode;
			slotMetrics: {
				groups: Date[][];
				getRange: (a: Date, b: Date, ignoreMin: boolean, ignoreMax: boolean) => {
					top: number;
					height: number;
				};
			};
		}) {
			if (!slotMetrics?.groups) return <>{children}</>;
			if (!puedeAgendarEnCalendario) return <>{children}</>;
			const strips: React.ReactNode[] = [];
			for (const grp of slotMetrics.groups) {
				for (const slotValue of grp) {
					if (!(slotValue instanceof Date)) continue;
					if (!slotKeysConTurno.has(thirtyMinSlotKey(slotValue))) continue;
					const end = new Date(slotValue.getTime() + 30 * 60 * 1000);
					const r = slotMetrics.getRange(slotValue, end, false, false);
					const slotCopy = new Date(slotValue.getTime());
					const k = `turnos-franja-${thirtyMinSlotKey(slotValue)}`;
					strips.push(
						<div
							key={k}
							className="turnos-rbc-franja-dashed"
							style={{
								position: 'absolute',
								top: `${r.top}%`,
								height: `${r.height}%`,
								right: 0,
								width: '30%',
								minWidth: '2.75rem',
							}}
							role="button"
							tabIndex={0}
							onClick={(e) => {
								e.stopPropagation();
								e.preventDefault();
								openNewTurnoAt(slotCopy);
							}}
							onKeyDown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.stopPropagation();
									e.preventDefault();
									openNewTurnoAt(slotCopy);
								}
							}}
							onMouseDown={(e) => e.stopPropagation()}
							title={
								currentView === 'week'
									? `Agendar turno — ${formatHoraCorta(slotValue)}. La columna de turnos queda a la izquierda; +N (si hay varios a la hora) y esta franja a la derecha.`
									: `Agendar turno — ${formatHoraCorta(slotValue)}. Los turnos quedan en el 70% izquierdo; esta franja es solo la zona punteada.`
							}
						/>
					);
				}
			}
			if (strips.length === 0) return <>{children}</>;
			return (
				<div className="turnos-rbc-event-container-wrap">
					<div className="turnos-rbc-events-left">{children}</div>
					{strips}
				</div>
			);
		};
	}, [slotKeysConTurno, openNewTurnoAt, currentView, puedeAgendarEnCalendario]);

	// Wrapper que react-big-calendar usa para cada sub-slot de 30 min en day/week.
	// Nos pasa `value` con la Date exacta del slot, así el click abre el modal
	// con la hora correcta sin depender de cálculos por pixel.
	const TimeSlotWrapper = useMemo(() => {
		return ({ value, children }: { value: Date; children: React.ReactElement }) => {
			const child = React.Children.only(children) as React.ReactElement<any>;
			const inTimeGrid = currentView === 'day' || currentView === 'week';
			if (!puedeAgendarEnCalendario) {
				return child;
			}
			return React.cloneElement(child, {
				onClick: (e: React.MouseEvent) => {
					e.stopPropagation();
					openNewTurnoAt(value);
				},
				title: inTimeGrid
					? enModoAgendarEstudio
						? `Asignar estudio — ${formatHoraCorta(value)}`
						: `Nuevo turno — ${formatHoraCorta(value)}. Clic en la grilla o en la franja punteada (si hay turnos en esta franja).`
					: undefined,
				style: { ...(child.props?.style || {}), cursor: 'pointer' },
			});
		};
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [currentView, openNewTurnoAt, puedeAgendarEnCalendario, enModoAgendarEstudio]);

	const RbcEventWithTooltip = useCallback(
		(p: { event: CalendarEvent; title?: React.ReactNode }) => {
			const r = p.event.resource;
			if (isOverflowResource(r)) {
				const overflowTip = `${r.extraCount} turno(s) a la misma hora (vista semana, colapsado en +${r.extraCount}). Clic para abrir el día a esta franja.`;
				return (
					<Tooltip
						title={overflowTip}
						enterDelay={300}
						placement="top"
					>
						<span
							className="rbc-event-overflow-chip"
							style={{
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								width: '100%',
								height: '100%',
								fontSize: '0.85rem',
								fontWeight: 800,
							}}
						>
							+{r.extraCount}
						</span>
					</Tooltip>
				);
			}
			const t = r;
			const kindMeta = getTurnoKindMeta(t);
			const parts = [
				`Tipo: ${kindMeta.label}`,
				`Estado: ${t.estado}`,
				t.recurso?.nombre ? `Recurso: ${t.recurso.nombre}` : '',
				t.motivo_reserva || t.motivo_consulta || '',
			].filter(Boolean);
			/* Vista día: una sola línea de hora (showTime=false oculta label nativo duplicado). */
			const timeRange = `${formatHoraCorta(p.event.start)}–${formatHoraCorta(p.event.end)}`;
			if (currentView === 'day') {
				return (
					<Tooltip title={parts.length ? parts.join(' · ') : ''} enterDelay={280} placement="right">
						<Box
							className="turnos-day-event-card"
							sx={{
								display: 'flex',
								flexDirection: 'column',
								justifyContent: 'flex-start',
								gap: 0.15,
								width: '100%',
								height: '100%',
								minHeight: 0,
								px: 0.5,
								py: 0.15,
								boxSizing: 'border-box',
								overflow: 'hidden',
							}}
						>
							<Typography
								variant="caption"
								sx={{ fontWeight: 700, lineHeight: 1.1, color: 'inherit', opacity: 0.95, fontSize: '0.68rem' }}
							>
								{timeRange}
							</Typography>
							<Typography
								variant="body2"
								sx={{
									fontWeight: 600,
									lineHeight: 1.2,
									fontSize: '0.8rem',
									color: 'inherit',
									overflow: 'hidden',
									display: '-webkit-box',
									WebkitLineClamp: 2,
									WebkitBoxOrient: 'vertical',
								}}
							>
								{p.title ?? p.event?.title}
							</Typography>
						</Box>
					</Tooltip>
				);
			}
			return (
				<Tooltip title={parts.join(' · ')} enterDelay={350} placement="top">
					<span
						style={{
							display: 'block',
							width: '100%',
							height: '100%',
							overflow: 'hidden',
							textOverflow: 'ellipsis',
							whiteSpace: 'nowrap',
						}}
					>
						{p.title ?? p.event?.title}
					</span>
				</Tooltip>
			);
		},
		[currentView]
	);

	const calendarComponents = useMemo(
		() => ({
			timeSlotWrapper: TimeSlotWrapper,
			event: RbcEventWithTooltip,
			eventContainerWrapper: turnoEventContainerWrapper,
		}),
		[TimeSlotWrapper, RbcEventWithTooltip, turnoEventContainerWrapper]
	);

	// Manejar selección de evento (clic en turno o en +N)
	const handleSelectEvent = (event: CalendarEvent) => {
		if (isOverflowResource(event.resource)) {
			const g = event.resource.goTo;
			const targetDay = new Date(g.getFullYear(), g.getMonth(), g.getDate(), 0, 0, 0, 0);
			const sameDayAsView =
				currentView === 'day' &&
				currentDate.getFullYear() === targetDay.getFullYear() &&
				currentDate.getMonth() === targetDay.getMonth() &&
				currentDate.getDate() === targetDay.getDate();
			if (!sameDayAsView) {
				setCurrentView('day');
				setCurrentDate(targetDay);
			}
			setForcedScrollToTime(
				new Date(
					g.getFullYear(),
					g.getMonth(),
					g.getDate(),
					g.getHours(),
					g.getMinutes(),
					0,
					0
				)
			);
			return;
		}
		const turno = event.resource;
		setEditingTurno(turno);
		setSelectedDateTime(null);
		setShowModal(true);
	};

	// Estilos de eventos según estado
	const eventStyleGetter = (event: CalendarEvent) => {
		if (isOverflowResource(event.resource)) {
			return {
				style: {
					backgroundColor: '#475569',
					borderColor: '#334155',
					borderRadius: '6px',
					opacity: 0.95,
					color: 'white',
					border: '1px dashed rgba(255, 255, 255, 0.45)',
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					cursor: 'pointer',
					fontWeight: 700,
				},
			};
		}
		const color = getTurnoEstadoColor(event.resource.estado);
		const kind = getTurnoAgendaKind(event.resource);
		const kindAccent =
			kind === 'estudio'
				? { boxShadow: 'inset 4px 0 0 rgba(255,255,255,0.55)' }
				: kind === 'procedimiento'
					? { boxShadow: 'inset 4px 0 0 rgba(0,0,0,0.2)' }
					: {};
		const dayExtras =
			currentView === 'day'
				? {
						border: '1px solid rgba(255, 255, 255, 0.45)',
						boxShadow: '0 1px 3px rgba(15, 23, 42, 0.2)',
					}
				: {};
		return {
			style: {
				backgroundColor: color,
				borderColor: color,
				borderRadius: '4px',
				opacity: 0.9,
				color: 'white',
				border: 'none',
				display: 'block',
				cursor: 'pointer',
				...kindAccent,
				...dayExtras,
			},
		};
	};

	const isInitialCatalogLoading =
		dataLoading.turnos ||
		dataLoading.pacientes ||
		dataLoading.medicos ||
		dataLoading.especialidades ||
		dataLoading.centrosFisicos ||
		dataLoading.tiposAtencion;

	if (!hasLoadedOnce && isInitialCatalogLoading) {
		return (
			<div className="dashboard">
				<div className="container">
					<div className="loading">🔄 Cargando turnos...</div>
				</div>
			</div>
		);
	}

	if (!puedeVerAgenda) {
		return (
			<Box className="dashboard" sx={{ p: 3 }}>
				<Typography variant="h5" gutterBottom>
					Agenda de turnos
				</Typography>
				<Typography variant="body1" color="text.secondary">
					Tu rol no tiene acceso a la agenda de turnos.
				</Typography>
			</Box>
		);
	}

	  return (
    <div className="dashboard fade-in">
      <div className="container">
        {/* Header */}
        <div className="turnos-header">
				<h1>📅 Turnos</h1>
			</div>

      {/* Search and Filters */}
      <Box sx={{ mb: 3, p: 3, borderRadius: 2, bgcolor: 'background.paper', boxShadow: 1 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField
            size="small"
            label="Buscar paciente"
            placeholder="Nombre o apellido..."
            value={filterPaciente}
            onChange={(e) => setFilterPaciente(e.target.value)}
            sx={{ minWidth: 220 }}
          />

          <Autocomplete
            options={medicoOptions}
            value={medicoSeleccionado}
            inputValue={medicoInputValue}
            onChange={(_, newValue) => {
              setFilterMedico(newValue ? String(newValue.id) : '');
              medicoInputReason.current = newValue ? 'selection' : 'clear';
              setMedicoInputValue(newValue ? `${newValue.nombre || ''} ${newValue.apellido || ''}`.trim() : '');
              if (newValue) {
                setMedicoOptions(prev => mergeUniqueById(prev, [newValue]));
              }
            }}
            onInputChange={(_, newInputValue, reason) => {
              if (reason === 'input') {
                medicoInputReason.current = 'input';
                setMedicoInputValue(newInputValue);
              } else if (reason === 'clear') {
                medicoInputReason.current = 'clear';
                setMedicoInputValue('');
                setMedicoOptions(medicosBase);
                setFilterMedico('');
              }
            }}
            loading={searchingMedicos}
            getOptionLabel={(option) => {
              const nombre = option.nombre || '';
              const apellido = option.apellido || '';
              const displayName = `${nombre} ${apellido}`.trim();
              return displayName ? `Dr. ${displayName}` : `Médico ${option.id}`;
            }}
            filterOptions={(options, state) => {
              const searchWords = extractSearchWords(state.inputValue);
              if (searchWords.length === 0) return options;
              return options.filter((option) => medicoMatchesSearch(option, searchWords));
            }}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Filtrar por médico"
                size="small"
                placeholder="Escribe al menos 2 letras..."
                sx={{ minWidth: 260 }}
              />
            )}
            noOptionsText={medicoInputValue.trim().length < 2 ? 'Escribe al menos 2 letras' : 'No se encontraron médicos'}
          />

          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Recurso / sala</InputLabel>
            <Select
              value={filterTipoRecurso}
              label="Recurso / sala"
              onChange={(e) => setFilterTipoRecurso(e.target.value)}
            >
              <MenuItem value="">Todos los recursos</MenuItem>
              <MenuItem value="CONSULTORIO">Consultorios</MenuItem>
              <MenuItem value="SALA_PROCEDIMIENTO">Salas de estudio</MenuItem>
              <MenuItem value="SALA_HEMODINAMIA">Hemodinamia</MenuItem>
              <MenuItem value="QUIROFANO">Quirófano</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Estado</InputLabel>
            <Select
              value={filterEstado}
              label="Estado"
              onChange={(e) => setFilterEstado(e.target.value)}
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="RESERVADO">Reservado</MenuItem>
              <MenuItem value="CONFIRMADO">Confirmado</MenuItem>
              <MenuItem value="REALIZADO">Realizado</MenuItem>
              <MenuItem value="CANCELADO">Cancelado</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 1, ml: 'auto' }}>
            {(filterPaciente || filterMedico || filterEstado || filterTipoRecurso || filterAgendaKind !== 'all') && (
              <Tooltip title="Limpiar filtros">
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => {
                    setFilterPaciente('');
                    setFilterMedico('');
                    setFilterEstado('');
                    setFilterTipoRecurso('');
                    setFilterAgendaKind('all');
                    setMedicoInputValue('');
                    setMedicoOptions(medicosBase);
                  }}
                >
                  <Clear fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            {userCanCreateTurno && (
              <Button
                variant="contained"
                color="primary"
                size="small"
                startIcon={<Add fontSize="small" />}
                onClick={() => {
                  setEditingTurno(null);
                  setSelectedDateTime(null);
                  setShowModal(true);
                }}
              >
                Nuevo turno
              </Button>
            )}
          </Box>
        </Box>

        <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mr: 0.5 }}>
            Ver:
          </Typography>
          {(['all', 'consulta', 'estudio'] as const).map((kind) => {
            const label =
              kind === 'all' ? 'Todos' : TURNO_KIND_META[kind].shortLabel + 's';
            const selected = filterAgendaKind === kind;
            return (
              <Chip
                key={kind}
                label={label}
                size="small"
                clickable
                color={selected ? 'primary' : 'default'}
                variant={selected ? 'filled' : 'outlined'}
                onClick={() => setFilterAgendaKind(kind === 'all' ? 'all' : kind)}
              />
            );
          })}
        </Box>

        <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <FilterList sx={{ fontSize: 18, color: 'text.secondary' }} />
          <Typography variant="body2" color="text.secondary">
            Mostrando {filteredTurnos.length} de {turnos.length} turnos
          </Typography>
          {(filterPaciente || filterMedico || filterEstado || filterTipoRecurso || filterAgendaKind !== 'all') && (
            <Chip label="Filtros activos" size="small" color="primary" variant="outlined" />
          )}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', ml: { sm: 'auto' }, alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
              Estado:
            </Typography>
            {TURNO_ESTADOS_CALENDARIO.map((est) => {
              const selected = filterEstado === est.value;
              return (
                <Chip
                  key={est.value}
                  size="small"
                  clickable
                  variant={selected ? 'filled' : 'outlined'}
                  label={est.label}
                  onClick={() => setFilterEstado(selected ? '' : est.value)}
                  sx={{
                    borderColor: est.color,
                    ...(selected
                      ? { bgcolor: est.color, color: '#fff', '&:hover': { bgcolor: est.color, opacity: 0.92 } }
                      : {
                          '& .MuiChip-label': { display: 'flex', alignItems: 'center', gap: 0.75 },
                        }),
                  }}
                  icon={
                    !selected ? (
                      <Box
                        component="span"
                        sx={{
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          bgcolor: est.color,
                          ml: 0.5,
                        }}
                      />
                    ) : undefined
                  }
                />
              );
            })}
          </Box>
        </Box>
      </Box>

			{enModoAgendarEstudio && estudioAgendaPendiente && (
				<Alert
					severity="info"
					sx={{ mt: 2 }}
					action={
						<Button color="inherit" size="small" startIcon={<Close />} onClick={clearEstudioAgendaPendiente}>
							Cancelar
						</Button>
					}
				>
					<strong>Asignar turno de estudio:</strong> elegí día y hora en el calendario para el estudio #
					{estudioAgendaPendiente.id}
					{estudioAgendaPendiente.tipo_estudio_nombre
						? ` (${estudioAgendaPendiente.tipo_estudio_nombre})`
						: ''}
					. Al hacer clic en una franja horaria se abrirá el formulario con los datos cargados.
				</Alert>
			)}

			{agendaReadOnly && (
				<Box
					role="note"
					sx={{
						mt: 2,
						p: 1.5,
						borderRadius: 2,
						border: (t) => `1px solid ${t.palette.warning.main}`,
						bgcolor: (t) =>
							t.palette.mode === 'dark' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(245, 158, 11, 0.08)',
					}}
				>
					<Typography variant="body2" color="text.secondary">
						<strong>Solo lectura (enfermería):</strong> podés ver la agenda institucional, pero no crear ni
						modificar turnos desde esta pantalla.
					</Typography>
				</Box>
			)}

			{currentView === 'day' && puedeAgendarEnCalendario && (
				<Box
					role="note"
					sx={{
						mt: 2,
						p: 1.5,
						borderRadius: 2,
						display: 'flex',
						alignItems: 'center',
						gap: 2,
						flexWrap: 'wrap',
						border: (t) => `1px solid ${t.palette.divider}`,
						bgcolor: (t) =>
							t.palette.mode === 'dark' ? 'rgba(59, 130, 246, 0.08)' : 'rgba(59, 130, 246, 0.06)',
					}}
				>
					<Chip
						size="small"
						variant="outlined"
						color="primary"
						label="Franja libre"
						sx={{ fontWeight: 600, borderStyle: 'dashed' }}
					/>
					<Typography variant="body2" color="text.secondary" sx={{ flex: 1, minWidth: 200 }}>
						Los turnos quedan en el <strong>lado izquierdo</strong> (la franja punteada no los tapa).
						Se muestran <strong>todos</strong> apilados para <strong>editar</strong>. La{' '}
						<strong>franja</strong> a la derecha es para <strong>agendar otro</strong>. En{' '}
						<strong>semana</strong>, si hay varios a la misma hora solo verás <strong>+N</strong> y la
						franja.
					</Typography>
				</Box>
			)}

			{/* Calendario Interactivo */}
			<Box
				sx={{
					mt: 2,
					/* Vista día: más alto para que cada franja horaria sea claramente legible */
					height: currentView === 'day' ? { xs: '75vh', md: 'min(88vh, 960px)' } : '720px',
					minHeight: currentView === 'day' ? 640 : undefined,
				}}
				className={`turnos-rbc-shell${currentView === 'day' ? ' turnos-rbc--day' : ''}${
					currentView === 'day' || currentView === 'week' ? ' turnos-rbc--time' : ''
				}`}
			>
				<BigCalendar
					localizer={localizer}
					events={displayCalendarEvents}
					startAccessor="start"
					endAccessor="end"
					style={{ height: '100%' }}
					view={currentView}
					onView={(view: string) => setCurrentView(view as 'month' | 'week' | 'day')}
					date={currentDate}
					onNavigate={(date: Date) => setCurrentDate(date)}
					views={['month', 'week', 'day']}
					defaultView="week"
					onSelectSlot={puedeAgendarEnCalendario ? handleSelectSlot : undefined}
					onSelectEvent={handleSelectEvent}
					selectable={puedeAgendarEnCalendario}
					step={30}
					timeslots={2}
					min={calendarMinTime}
					max={calendarMaxTime}
					scrollToTime={forcedScrollToTime ?? calendarScrollToTime}
					components={calendarComponents}
					eventPropGetter={eventStyleGetter}
					messages={{
						next: 'Siguiente',
						previous: 'Anterior',
						today: 'Hoy',
						month: 'Mes',
						week: 'Semana',
						day: 'Día',
						noEventsInRange: 'No hay turnos en este período',
						showMore: (total: number) => `+ ${total} más`,
					}}
					culture="es"
				/>
			</Box>

			{/* Modal Turno */}
			<TurnoDrawer
				key={
					editingTurno
						? `edit-${editingTurno.id}`
						: estudioAgendaPendiente
							? `estudio-${estudioAgendaPendiente.id}-${selectedDateTime?.getTime() ?? 'slot'}`
							: 'new'
				}
				open={showModal}
				onClose={() => {
					setShowModal(false);
					setEditingTurno(null);
					setSelectedDateTime(null);
				}}
				editingTurno={editingTurno}
				selectedDateTime={selectedDateTime}
				initialAgendaTipo={estudioAgendaPendiente ? 'estudio' : undefined}
				initialEstudio={estudioAgendaPendiente}
				forceReadOnly={
					agendaReadOnly ||
					(editingTurno
						? !canEditTurno(currentUser, editingTurno)
						: enModoAgendarEstudio
							? false
							: !userCanCreateTurno)
				}
				onSuccess={async () => {
					try {
						await refreshTurnos();
						setShowModal(false);
						setEditingTurno(null);
						setSelectedDateTime(null);
						clearEstudioAgendaPendiente();
					} catch {
						// El modal ya mostró feedback; no interrumpir el cierre
					}
				}}
				onOpenAtencion={(atencionId) => {
					setSelectedAtencionId(atencionId);
				}}
			/>

			{/* Drawer de Atención - FUERA del modal para evitar resets */}
			<AtencionDetailDrawer
				atencionId={selectedAtencionId}
				open={Boolean(selectedAtencionId)}
				onClose={() => {
					setSelectedAtencionId(null);
				}}
				currentUserRole={currentUser?.rol}
				onIntervencionSaved={refreshTurnos}
			/>
		</div>
		</div>
	);
};

export default Turnos; 