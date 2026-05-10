#!/usr/bin/env python3
import argparse
import logging
from datetime import date, datetime
from pathlib import Path
from cybernetics.daily_loop import CyberneticDailyLoop

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vibe-ops-cli")

def update_implementation_log(base_path: Path, message: str):
    log_path = base_path / "IMPLEMENTATION_LOG.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n- [{timestamp}] {message}\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        logger.error(f"Erro ao atualizar IMPLEMENTATION_LOG: {e}")

def main():
    parser = argparse.ArgumentParser(description="Vibe-Ops - Cybernetic Orchestrator CLI")
    
    # Comandos principais
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")
    
    # Comando: run-daily
    run_parser = subparsers.add_parser("run-daily", help="Executa o ciclo diário cibernético (Target-Sensor-Adjuster)")
    run_parser.add_argument("--date", type=str, help="Data alvo (YYYY-MM-DD), default: hoje")
    run_parser.add_argument("--db", type=str, default="vibe_ops.db", help="Path para o banco SQLite")
    run_parser.add_argument("--tw-path", type=str, help="Path para o diretório Taskwarrior")
    run_parser.add_argument("--vault-path", type=str, help="Path para o Obsidian Vault")
    
    # Comando: status
    status_parser = subparsers.add_parser("status", help="Exibe o status atual do sistema (Policy + Ikigai)")
    status_parser.add_argument("--db", type=str, default="vibe_ops.db", help="Path para o banco SQLite")

    # Comando: gaps
    gaps_parser = subparsers.add_parser("gaps", help="Busca por gaps cognitivos e de execução")
    gaps_parser.add_argument("--db", type=str, default="vibe_ops.db", help="Path para o banco SQLite")

    # Comando: sync
    sync_parser = subparsers.add_parser("sync", help="Sincroniza Obsidian -> SQLite -> Taskwarrior")
    sync_parser.add_argument("--db", type=str, default="vibe_ops.db", help="Path para o banco SQLite")
    sync_parser.add_argument("--tw-path", type=str, help="Path para o diretório Taskwarrior")
    sync_parser.add_argument("--vault-path", type=str, help="Path para o Obsidian Vault")

    args = parser.parse_args()
    
    base_path = Path(__file__).resolve().parent.parent

    if args.command == "run-daily":
        target_date = date.fromisoformat(args.date) if args.date else date.today()
        
        # Default paths se não fornecidos
        tw_path = args.tw_path or str(base_path / "taskwarrior")
        vault_path = args.vault_path or str(base_path / "life" / "vibe-ops" / "vault")
        
        logger.info(f"Iniciando ciclo cibernético para {target_date}...")
        
        try:
            loop = CyberneticDailyLoop(
                db_path=args.db,
                tw_path=tw_path,
                vault_path=vault_path
            )
            
            decision = loop.execute_daily_cycle(target_date)
            
            msg = f"Ciclo completo para {target_date}. Nova Policy: {decision.policy.value} (Severidade: {decision.infrações_24h} infrações)"
            logger.info(msg)
            update_implementation_log(base_path, msg)
            
        except Exception as e:
            err_msg = f"FALHA no ciclo cibernético: {str(e)}"
            logger.error(err_msg, exc_info=True)
            update_implementation_log(base_path, err_msg)
            sys.exit(1)
            
    elif args.command == "status":
        from pipeline.ikigai_scorer import IkigaiScorer
        from pipeline.policy_engine import PolicyEngine
        
        logger.info("Recuperando status cibernético...")
        try:
            loop = CyberneticDailyLoop(db_path=args.db, tw_path="", vault_path="")
            decision = loop._get_previous_decision(date.today())
            ikigai_data = loop.ikigai.compute_score()
            
            print("\n" + "="*40)
            print(" VIBE-OPS CYBERNETIC STATUS ".center(40, "="))
            print("="*40)
            if decision:
                print(f"Data:       {decision.date}")
                print(f"Política:   {decision.policy.value}")
                print(f"Budget HW:  {decision.hardwork_budget_hours}h")
                print(f"Duração:    {decision.days_in_current_policy} dias")
            else:
                print("Nenhuma decisão de política encontrada.")
            
            print("-" * 40)
            print(" IKIGAI VECTORS ".center(40, "-"))
            print(f"Global:     {ikigai_data.get('global', 0):.2f}")
            print(f"Estudo:     {ikigai_data.get('study', 0):.2f}")
            print(f"Dev:        {ikigai_data.get('dev', 0):.2f}")
            print(f"Saúde:      {ikigai_data.get('health', 0):.2f}")
            print("="*40 + "\n")
            
        except Exception as e:
            logger.error(f"Erro ao recuperar status: {e}")
            sys.exit(1)

    elif args.command == "gaps":
        from cybernetics.engine import BinaryKnowledgeTree, GapSearchEngine
        
        logger.info("Analisando gaps cognitivos e de execução...")
        try:
            kb_tree = BinaryKnowledgeTree(args.db)
            gap_engine = GapSearchEngine(args.db)
            
            cognitive_gaps = kb_tree.get_cognitive_gaps()
            execution_debt = gap_engine.analyze_execution_debt()
            
            print("\n" + "="*40)
            print(" COGNITIVE GAPS (Next Priorities) ".center(40, "="))
            print("="*40)
            if cognitive_gaps:
                for gap in cognitive_gaps:
                    print(f"- {gap['topic']} ({gap['current_progress']*100:.1f}%)")
                    print(f"  {gap['reason']}")
            else:
                print("Nenhum gap cognitivo imediato detectado.")
                
            print("-" * 40)
            print(" EXECUTION DEBT ".center(40, "-"))
            print(f"Target:     {execution_debt['target']}h/dia")
            print(f"Real (3d):  {execution_debt['actual_3d_avg']:.2f}h/dia")
            print(f"Gap:        {execution_debt['gap_hours']:.2f}h")
            print(f"Débito:     {execution_debt['debt_percentage']:.1f}%")
            print("="*40 + "\n")
            
        except Exception as e:
            logger.error(f"Erro na análise de gaps: {e}")
            sys.exit(1)
            
    elif args.command == "sync":
        # Default paths se não fornecidos
        tw_path = args.tw_path or str(base_path / "taskwarrior")
        vault_path = args.vault_path or str(base_path / "life" / "vibe-ops" / "vault")
        
        logger.info("Iniciando sincronização global...")
        try:
            loop = CyberneticDailyLoop(
                db_path=args.db,
                tw_path=tw_path,
                vault_path=vault_path
            )
            
            # 1. Ingestão: Obsidian -> SQLite
            logger.info("Sincronizando Obsidian -> SQLite...")
            stats_obs = loop.sync.sync_obsidian_to_sqlite()
            logger.info(f"Obsidian Sync: {stats_obs}")
            
            # 2. Feedback: Taskwarrior -> SQLite (Completed tasks)
            logger.info("Sincronizando Taskwarrior -> SQLite (Feedback)...")
            stats_tw_back = loop.sync.sync_taskwarrior_to_sqlite()
            logger.info(f"TW Feedback Sync: {stats_tw_back}")
            
            # 3. Distribuição: SQLite -> Taskwarrior (Injection)
            # Recupera política atual para o throttle
            decision = loop._get_previous_decision(date.today())
            policy = decision.policy.value if decision else "MAINTAIN"
            
            logger.info(f"Sincronizando SQLite -> Taskwarrior (Política: {policy})...")
            stats_tw = loop.sync.sync_sqlite_to_taskwarrior(policy)
            logger.info(f"Taskwarrior Injection: {stats_tw}")
            
            msg = "Sincronização global concluída com sucesso."
            logger.info(msg)
            update_implementation_log(base_path, msg)
            
        except Exception as e:
            err_msg = f"FALHA na sincronização: {str(e)}"
            logger.error(err_msg, exc_info=True)
            update_implementation_log(base_path, err_msg)
            sys.exit(1)
            
    else:
        parser.print_help()

if __name__ == "__main__":
    import sys
    main()
