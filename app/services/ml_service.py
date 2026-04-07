from typing import Dict


class MLService:
    """
    Servicio placeholder para fase Random Forest.
    Mantiene contrato estable para enchufar modelo real sin romper API.
    """

    def predict_adjustment(self, scores: Dict[str, float]) -> Dict[str, float]:
        # Esta logica no reemplaza reglas; solo ajusta confianza en fase MVP.
        adjustment = 0.0
        if scores.get("moisture", 0) < 0.3:
            adjustment -= 0.05
        if scores.get("stress", 0) > 0.7:
            adjustment -= 0.05

        return {
            "confidence_delta": adjustment,
            "model_version": "rf_placeholder_v0",
        }
