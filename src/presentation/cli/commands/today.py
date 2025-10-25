"""Today command - Display tasks for today."""

import click

from application.queries.filters.composite_filter import CompositeFilter
from application.queries.filters.today_filter import TodayFilter
from presentation.cli.commands.common_options import filter_options, sort_options
from presentation.cli.commands.filter_helpers import build_task_filter
from presentation.cli.commands.table_helpers import get_and_filter_tasks, render_table
from presentation.cli.context import CliContext
from presentation.cli.error_handler import handle_command_errors


@click.command(
    name="today",
    help="Display tasks for today (shows incomplete tasks by default).",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["table"]),
    default="table",
    help="Display format (default: table)",
)
@sort_options(default_sort="deadline")
@filter_options()
@click.pass_context
@handle_command_errors("displaying tasks")
def today_command(ctx, format, all, status, sort, reverse):
    """Display tasks for today.

    Shows tasks that meet any of these criteria:
    - Deadline is today
    - Planned period includes today (planned_start <= today <= planned_end)
    - Status is IN_PROGRESS

    By default, shows incomplete tasks (PENDING, IN_PROGRESS) only.
    Use -a/--all to include all tasks (including archived).
    Use --status to filter by specific status.
    """
    ctx_obj: CliContext = ctx.obj
    repository = ctx_obj.repository

    # Build filter: TodayFilter + status/all filter (AND logic)
    today_filter = TodayFilter()
    status_filter = build_task_filter(all=all, status=status)

    # Combine TodayFilter with status filter
    filter_obj = CompositeFilter([status_filter, today_filter]) if status_filter else today_filter

    # Get filtered and sorted tasks
    today_tasks = get_and_filter_tasks(repository, filter_obj, sort_by=sort, reverse=reverse)

    # Render using shared table renderer
    render_table(ctx_obj, today_tasks)
