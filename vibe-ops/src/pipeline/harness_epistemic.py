from typing import List, Dict
from models import StudyTopic, Project

class EpistemicHarness:
    """
    Harness para priorização epistêmica e sugestão de estudos.
    """
    
    SYSTEM_PROMPT = """
    Você é o Hypervisor do sistema 'Memory Machine'. Sua tarefa é avaliar o 'Débito Cognitivo' 
    e priorizar o esforço epistêmico do usuário baseado em roadmaps de software e o vetor IKIGAi 'Revenue'.
    """

    @classmethod
    def generate_study_query(cls, roadblock_task: str, project: Project) -> str:
        """Gera uma query para pesquisar pré-requisitos em fontes indexadas."""
        return f"Quais são os conceitos fundamentais e bibliotecas necessárias para implementar {roadblock_task} no projeto {project.title}?"

    @classmethod
    def evaluate_priority(cls, topic: StudyTopic, projects: List[Project]) -> float:
        """
        Calcula o score de prioridade de um tópico baseado no contexto.
        Score = (Impacto Revenue) * (N de Projetos Vinculados) / (Profundidade Atual + 1)
        """
        revenue_weight = {"CRITICAL": 5.0, "HIGH": 3.0, "MEDIUM": 1.5, "LOW": 1.0, "NONE": 0.5}
        max_impact = max([revenue_weight.get(p.revenue_impact, 1.0) for p in projects]) if projects else 1.0
        n_links = len(projects)
        return (max_impact * (n_links + 1)) / (topic.depth_level + 1)
