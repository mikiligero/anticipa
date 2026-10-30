import React from "react";
import { AVISO_SIMULACION } from "./predicciones.js";
export default function AvisoSimulacion() {
  return <div role="note" className="aviso-simulacion">
    <strong>PREDICCIÓN SIMULADA</strong><div>{AVISO_SIMULACION}</div>
  </div>;
}
