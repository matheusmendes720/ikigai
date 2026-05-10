from datetime import date, datetime
from typing import List, Dict, Any, Optional
from schemas.pydantic_v2 import PolicyState, PolicyDecision

class PolicyEngine:
    """
    Motor de Decisão Cibernética (Adjuster).
    Calcula a política de execução baseada em desvios e métricas.
    """
    
    # Configurações de Setpoints por Política
    POLICY_MAP = {
        PolicyState.PUSH: {
            "hardwork_budget": 4.0,
            "pause_minutes": 10,
            "sleep_target": 7.5,
            "qhe_target": 0.85,
            "c_comp_target": 0.90
        },
        PolicyState.MAINTAIN: {
            "hardwork_budget": 2.5,
            "pause_minutes": 15,
            "sleep_target": 8.0,
            "qhe_target": 0.65,
            "c_comp_target": 0.85
        },
        PolicyState.REDUCE: {
            "hardwork_budget": 1.5,
            "pause_minutes": 20,
            "sleep_target": 8.5,
            "qhe_target": 0.45,
            "c_comp_target": 0.75
        },
        PolicyState.RECOVER: {
            "hardwork_budget": 0.5,
            "pause_minutes": 30,
            "sleep_target": 9.0,
            "qhe_target": 0.25,
            "c_comp_target": 0.65
        }
    }

    def evaluate(self, 
                 metrics: Dict[str, Any], 
                 prev_decision: Optional[PolicyDecision] = None,
                 target_date: Optional[date] = None) -> PolicyDecision:
        """
        Avalia as métricas e determina a nova decisão de política.
        """
        target_date = target_date or date.today()
        prev_policy = prev_decision.policy if prev_decision else PolicyState.MAINTAIN
        days_in_policy = prev_decision.days_in_current_policy if prev_decision else 1
        
        # 1. Calcular Severidade do Desvio
        severity = self._calculate_severity(metrics)
        alertas = []
        recomendacoes = []

        # 2. Lógica de Transição (Máquina de Estados Cibernética)
        new_policy = prev_policy
        
        if severity == "CRITICAL":
            new_policy = PolicyState.RECOVER
            alertas.append("Severidade CRÍTICA detectada. Forçando RECOVER.")
        elif severity == "HIGH":
            if prev_policy == PolicyState.PUSH:
                new_policy = PolicyState.MAINTAIN
            else:
                new_policy = PolicyState.REDUCE
            alertas.append("Desvio ALTO. Reduzindo intensidade.")
        elif severity == "LOW" and metrics.get("consistency", 0) > 0.9:
            # Histerese: Só sobe para PUSH se estiver consistente por tempo suficiente
            if prev_policy == PolicyState.MAINTAIN and days_in_policy >= 3:
                new_policy = PolicyState.PUSH
                recomendacoes.append("Consistência alta por 3 dias. Sugerindo PUSH.")
            elif prev_policy in [PolicyState.REDUCE, PolicyState.RECOVER]:
                new_policy = PolicyState.MAINTAIN
                recomendacoes.append("Recuperação detectada. Retornando a MAINTAIN.")

        # Se mudou a política, reseta o contador de dias
        if new_policy != prev_policy:
            days_in_policy = 1
        else:
            days_in_policy += 1

        # 3. Aplicar Setpoints
        sp = self.POLICY_MAP.get(new_policy, self.POLICY_MAP[PolicyState.MAINTAIN])
        
        return PolicyDecision(
            date=target_date,
            policy=new_policy,
            qhe=sp["qhe_target"],
            c_comp=sp["c_comp_target"],
            infrações_24h=metrics.get("infractions", 0),
            tipo_dia="workday", # Pode ser expandido para weekend/holiday
            hardwork_budget_hours=sp["hardwork_budget"],
            pause_duration_minutes=sp["pause_minutes"],
            sleep_target_hours=sp["sleep_target"],
            recomendacoes=recomendacoes,
            alertas=alertas,
            days_in_current_policy=days_in_policy,
            policy_prev=prev_policy,
            computed_at=datetime.utcnow()
        )

    def _calculate_severity(self, metrics: Dict[str, Any]) -> str:
        """Determina a severidade do desvio baseada em regras heurísticas."""
        infractions = metrics.get("infractions", 0)
        consistency = metrics.get("consistency", 1.0)
        hours_dev = metrics.get("hours_deviation", 0.0)

        if infractions >= 3 or consistency < 0.5:
            return "CRITICAL"
        if infractions >= 1 or hours_dev > 1.5 or consistency < 0.75:
            return "HIGH"
        if hours_dev > 0.5 or consistency < 0.85:
            return "MEDIUM"
        return "LOW"
