// Ejemplos fijos para la demo. No proceden del feed ni de un modelo entrenado.
export const AVISO_SIMULACION = "Las predicciones reales estarán disponibles tras entrenar el modelo.";
export const PREDICCION_VIAJERO = Object.freeze({
  prob_llegar_bien: 87, umbral_grave_min: 10, retraso_final_min: 4,
  confianza: "Alta", nivel_previsto: "moderado",
});
export const PREDICCION_OPERADOR = Object.freeze({
  alertas: 2, trenes: 8, retrasoFinal: 12, probabilidad: 94, confianza: "alta",
});
