import typer
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from pipeline.sync_orchestrator import SyncOrchestrator
from pipeline.reverse_sync import ReverseSync
from pipeline.ingestion_engine import IngestionEngine
from pipeline.unified_router import UnifiedQueryRouter
from pipeline.cognitive_debt_tracker import CognitiveDebtTracker
from pipeline.mvl_orchestrator import MVLOrchestrator
from pipeline.schema_registry import SchemaRegistry
from pipeline.frontmatter_parser import FrontmatterParser
from storage.data_mesh_adapter import DataMeshAdapter
from storage.orm import Base
from pipeline.gap_engine import GapSearchEngine

app = typer.Typer(help="Vibe-Ops: Cybernetic Data Mesh Dashboard")
console = Console()

# Fix Unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Setup High-Performance Engine
db_path = "vibe_ops.db"
engine = create_engine(f"sqlite:///{db_path}")
Session = sessionmaker(bind=engine)
session = Session()

adapter = DataMeshAdapter(db_path=db_path)
registry = SchemaRegistry()
orchestrator = MVLOrchestrator(session, adapter.chroma, registry=registry)
router = UnifiedQueryRouter(session, adapter.chroma)
debt_tracker = CognitiveDebtTracker(adapter)
gap_engine = GapSearchEngine(adapter)

@app.command()
def sync_file(path: str, domain: str = "study"):
    """Sincroniza um único arquivo Markdown via Master Orchestrator."""
    console.print(f"[bold blue]⚡ Master Orchestrator:[/bold blue] {path}")
    
    # 1. Parse Raw
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    raw_yaml = FrontmatterParser.extract_raw(content)
    if not raw_yaml:
        console.print("[bold red]Erro:[/bold red] Frontmatter não encontrado.")
        return

    # 2. Execute High-Performance Ingestion
    success = orchestrator.ingest_markdown(
        file_path=path,
        raw_yaml=raw_yaml,
        content=content,
        domain=domain
    )

    if success:
        console.print(f"[bold green]✅ Ingestão Concluída para {path}[/bold green]")
    else:
        console.print(f"[bold red]❌ Falha na Ingestão. Verifique a Máquina de Estados.[/bold red]")

@app.command()
def debt_dashboard(threshold: float = 0.25):
    """Visualiza o Dashboard de Débito Cognitivo."""
    critical_topics = debt_tracker.identify_critical_debt(threshold)
    
    table = Table(title=f"🛑 Dashboard de Débito Cognitivo (Interest > {threshold})")
    table.add_column("ID", style="cyan")
    table.add_column("Tópico", style="white")
    table.add_column("Importância", style="magenta")
    table.add_column("Juros (%)", style="red")

    for topic in critical_topics:
        table.add_row(
            topic["id"],
            topic["title"],
            topic["importance"],
            f"{topic['interest']*100:.1f}%"
        )

    console.print(table)
    if not critical_topics:
        console.print("[green]Nenhum débito crítico detectado. Eficiência epistêmica nominal.[/green]")

@app.command()
def hybrid_search(query: str, domain: str = "study"):
    """Executa busca profunda (Deep Join) no Data Mesh."""
    results = router.query_mesh(domain=domain, semantic_query=query)
    
    console.print(Panel(f"Resultados para: [bold yellow]'{query}'[/bold yellow] em [bold cyan]{domain}[/bold cyan]"))
    
    for res in results:
        console.print(f"\n[bold green]UEID:[/bold green] {res['ueid']}")
        console.print(f"[bold dim]Contrato:[/bold dim] {res['catalog']['contract']}")
        console.print(f"[italic]'{res['document'][:200]}...'[/italic]")
        
        # Mostra dados estruturados se disponíveis
        if res['structured']:
            structured_str = ", ".join([f"{k}: {v}" for k, v in res['structured'].items() if k != 'id'])
            console.print(f"[bold blue]SQL Data:[/bold blue] {structured_str}")
        console.print("-" * 40)

@app.command()
def gaps(domain: str = "study"):
    """Detecta lacunas de conhecimento e dívida de execução."""
    console.print(Panel("[bold yellow]🔍 Iniciando Scan de Lacunas Cognitivas & Execução[/bold yellow]"))
    
    analysis = gap_engine.analyze_gaps(domain)
    
    # 1. Cognitive Gaps
    table_cog = Table(title="🧠 Lacunas de Conexão Cognitiva")
    table_cog.add_column("Causa Raiz", style="cyan")
    table_cog.add_column("Grau de Isolamento", style="red")
    
    for gap in analysis["cognitive_gaps"]:
        table_cog.add_row(gap["cause"], f"{gap['isolation_degree']:.2f}")
    
    console.print(table_cog)
    
    # 2. Execution Debt
    table_exe = Table(title="⏳ Dívida de Execução vs Orçamento")
    table_exe.add_column("Métrica", style="white")
    table_exe.add_column("Valor", style="magenta")
    
    exe = analysis["execution_debt"]
    table_exe.add_row("Dívida de Horas (Backlog)", f"{exe['hours_debt']:.1f}h")
    table_exe.add_row("Capacidade Semanal (Budget)", f"{exe['weekly_capacity']:.1f}h")
    table_exe.add_row("Dias para Quitar", f"{exe['days_to_clear']:.1f} dias")
    
    console.print(table_exe)
    
    if exe["days_to_clear"] > 14:
        console.print(Panel("[bold red]⚠️ ALERTA: Saturação de Pipeline detectada! Considere entrar em modo PUSH ou reduzir escopo.[/bold red]"))

if __name__ == "__main__":
    app()
