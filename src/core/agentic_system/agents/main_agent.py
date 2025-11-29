"""Main agent."""

from datetime import UTC, datetime

from attr import dataclass
from pydantic_ai import Agent, ModelSettings, RunContext
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agentic_system.agents.rag_agent import run_rag_agent
from src.core.agentic_system.utils import get_chat_model
from src.services.prompt_service import PromptService


@dataclass
class MainAgentDependencies:
    """Main agent dependencies."""

    user_name: str
    session: AsyncSession
    redis: Redis


main_agent = Agent[MainAgentDependencies, str](
    name="Main Agent",
    model=get_chat_model("gpt-4o-mini", ModelSettings(temperature=0.3)),
    deps_type=MainAgentDependencies,
)


@main_agent.instructions
async def main_agent_instructions(
    ctx: RunContext[MainAgentDependencies],
) -> str:
    """Main agent instructions."""
    system_prompt = await PromptService.get_cached_content(
        session=ctx.deps.session,
        redis=ctx.deps.redis,
        slug="main_agent_instructions",
    )
    return system_prompt.format(
        user_name=ctx.deps.user_name,
        date_time=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
    )


@main_agent.tool
async def search_documents(
    ctx: RunContext[MainAgentDependencies],
    query: str,
) -> list[str]:
    """Search documents."""
    rag_agent_output = await run_rag_agent(
        query,
        ctx.deps.session,
        ctx.deps.redis,
    )
    return rag_agent_output.documents
