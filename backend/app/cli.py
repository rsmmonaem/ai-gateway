import asyncio
import sys
import time
from typing import Optional
import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from app.core.config import settings
from app.core.security import generate_api_key, get_password_hash
from app.database.init_db import init_db
from app.database.session import async_session_factory
from app.models.api_key import APIKey
from app.models.model_registry import ModelDefinition
from app.models.user import User
from app.providers.registry import provider_registry
from app.schemas.openai import ChatCompletionRequest, ChatMessage

app = typer.Typer(help="AI Gateway Command-Line Administration Tool")
user_app = typer.Typer(help="User management commands")
key_app = typer.Typer(help="API Key management commands")
model_app = typer.Typer(help="Model management commands")

app.add_typer(user_app, name="user")
app.add_typer(key_app, name="key")
app.add_typer(model_app, name="model")
console = Console()


def run_async(coro):
    return asyncio.run(coro)


@app.command()
def init():
    """Initialize database and seed bootstrap admin user & models."""
    async def _init():
        async with async_session_factory() as session:
            await init_db(session)
    run_async(_init())
    rprint("[bold green]Database initialized successfully![/bold green]")


@app.command()
def health():
    """Check health of AI Gateway and connected local inference backends."""
    async def _health():
        table = Table(title="AI Gateway Model Health Status")
        table.add_column("Model Slug", style="cyan")
        table.add_column("Backend", style="magenta")
        table.add_column("Endpoint", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Latency (ms)", justify="right")

        async with async_session_factory() as session:
            res = await session.execute(select(ModelDefinition))
            models = res.scalars().all()
            for m in models:
                provider = provider_registry.get_provider(
                    backend=m.backend,
                    endpoint=m.endpoint,
                    model_name=m.backend_model_name,
                    timeout=5.0,
                )
                is_healthy, status_str, latency = await provider.health_check()
                status_color = "green" if is_healthy else "red"
                lat_str = f"{latency:.1f}" if latency is not None else "-"
                table.add_row(m.slug, m.backend, m.endpoint, f"[{status_color}]{status_str}[/{status_color}]", lat_str)

        console.print(table)

    run_async(_health())


@user_app.command("create")
def create_user(
    email: str = typer.Option(..., prompt=True),
    name: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
    role: str = typer.Option("user", help="user or admin"),
):
    """Create a new user account."""
    async def _create():
        async with async_session_factory() as session:
            res = await session.execute(select(User).where(User.email == email))
            if res.scalar_one_or_none():
                rprint(f"[red]Error: User with email {email} already exists.[/red]")
                sys.exit(1)

            new_user = User(
                email=email,
                name=name,
                password_hash=get_password_hash(password),
                role=role,
                status="active",
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            rprint(f"[bold green]User created successfully! ID: {new_user.id} ({new_user.email})[/bold green]")

    run_async(_create())


@user_app.command("list")
def list_users():
    """List all registered users."""
    async def _list():
        table = Table(title="Registered Users")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Email", style="white")
        table.add_column("Name", style="yellow")
        table.add_column("Role", style="magenta")
        table.add_column("Status", style="green")

        async with async_session_factory() as session:
            res = await session.execute(select(User).order_by(User.id.asc()))
            users = res.scalars().all()
            for u in users:
                table.add_row(str(u.id), u.email, u.name, u.role, u.status)

        console.print(table)

    run_async(_list())


@key_app.command("create")
def create_key(
    email: str = typer.Option(..., help="User email to assign key to"),
    name: str = typer.Option("CLI Key", help="Display name for key"),
    rpm: int = typer.Option(60, help="Requests per minute limit"),
):
    """Generate a new API key for a user."""
    async def _create_key():
        async with async_session_factory() as session:
            res = await session.execute(select(User).where(User.email == email))
            user = res.scalar_one_or_none()
            if not user:
                rprint(f"[red]User '{email}' not found.[/red]")
                sys.exit(1)

            raw_key, key_hash, key_prefix = generate_api_key()
            new_key = APIKey(
                user_id=user.id,
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=name,
                rate_limit_rpm=rpm,
            )
            session.add(new_key)
            await session.commit()

            rprint("[bold green]API Key Generated Successfully![/bold green]")
            rprint(f"[bold yellow]Secret Key: {raw_key}[/bold yellow]")
            rprint("[dim]Note: Save this key now; it will never be displayed in plain text again.[/dim]")

    run_async(_create_key())


@key_app.command("revoke")
def revoke_key(key_id: int):
    """Revoke an API key by its ID."""
    from datetime import datetime, timezone

    async def _revoke():
        async with async_session_factory() as session:
            res = await session.execute(select(APIKey).where(APIKey.id == key_id))
            key = res.scalar_one_or_none()
            if not key:
                rprint(f"[red]Key ID {key_id} not found.[/red]")
                sys.exit(1)

            key.revoked_at = datetime.now(timezone.utc)
            await session.commit()
            rprint(f"[bold green]API Key {key.key_prefix} revoked.[/bold green]")

    run_async(_revoke())


@model_app.command("list")
def list_models():
    """List all registered models in the gateway."""
    async def _list():
        table = Table(title="AI Model Registry")
        table.add_column("Slug", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Backend", style="magenta")
        table.add_column("Endpoint", style="blue")
        table.add_column("Context", justify="right")
        table.add_column("Priority", justify="right")
        table.add_column("Enabled", justify="center")

        async with async_session_factory() as session:
            res = await session.execute(select(ModelDefinition).order_by(ModelDefinition.priority.desc()))
            for m in res.scalars().all():
                enabled_str = "[green]YES[/green]" if m.enabled else "[red]NO[/red]"
                table.add_row(m.slug, m.name, m.backend, m.endpoint, str(m.context_length), str(m.priority), enabled_str)

        console.print(table)

    run_async(_list())


@model_app.command("test")
def test_model(slug: str, prompt: str = "Hello from Apple Silicon M5!"):
    """Send a test prompt to a model backend and measure TTFT and total latency."""
    async def _test():
        async with async_session_factory() as session:
            res = await session.execute(select(ModelDefinition).where(ModelDefinition.slug == slug))
            model = res.scalar_one_or_none()
            if not model:
                rprint(f"[red]Model '{slug}' not found.[/red]")
                sys.exit(1)

            rprint(f"[cyan]Testing model '{model.slug}' on backend '{model.backend}' ({model.endpoint})...[/cyan]")
            provider = provider_registry.get_provider(
                backend=model.backend,
                endpoint=model.endpoint,
                model_name=model.backend_model_name,
                timeout=15.0,
            )

            t0 = time.time()
            try:
                chat_req = ChatCompletionRequest(
                    model=model.slug,
                    messages=[ChatMessage(role="user", content=prompt)],
                    max_tokens=40,
                )
                resp = await provider.chat_completion(chat_req)
                elapsed_ms = (time.time() - t0) * 1000
                rprint(f"[bold green]Success in {elapsed_ms:.1f}ms![/bold green]")
                if resp.choices:
                    rprint(f"[bold white]Response:[/bold white] {resp.choices[0].message.content}")
            except Exception as e:
                rprint(f"[bold red]Test Failed:[/bold red] {e}")

    run_async(_test())


if __name__ == "__main__":
    app()
