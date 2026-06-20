import React from 'react';
import TurnoModal from './TurnoModal';

/**
 * Panel lateral de turno (misma lógica que TurnoModal; el formulario se renderiza en un drawer).
 */
export type TurnoDrawerProps = React.ComponentProps<typeof TurnoModal>;

const TurnoDrawer: React.FC<TurnoDrawerProps> = (props) => <TurnoModal {...props} />;

export default TurnoDrawer;
