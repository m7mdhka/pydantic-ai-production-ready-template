"""RAG agent for the agentic system."""

from attr import dataclass
from pydantic_ai import Agent, ModelSettings, RunContext
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agentic_system.utils import get_chat_model
from src.services.prompt_service import PromptService


@dataclass
class RAGAgentDependencies:
    """Main agent dependencies."""

    session: AsyncSession
    redis: Redis


@dataclass
class RAGAgentOutput:
    """RAG agent output."""

    documents: list[str]


rag_agent = Agent[RAGAgentDependencies, RAGAgentOutput](
    name="RAG Agent",
    model=get_chat_model("gpt-4o-mini", ModelSettings(temperature=0.3)),
    deps_type=RAGAgentDependencies,
    output_type=RAGAgentOutput,
)


@rag_agent.instructions
async def rag_agent_instructions(
    ctx: RunContext[RAGAgentDependencies],
) -> str:
    """Main agent instructions."""
    return await PromptService.get_cached_content(
        session=ctx.deps.session,
        redis=ctx.deps.redis,
        slug="rag_agent_instructions",
    )


async def run_rag_agent(
    query: str,
    session: AsyncSession,
    redis: Redis,
) -> RAGAgentOutput:
    """Run the RAG agent."""
    agent_run = await rag_agent.run(
        user_prompt=query,
        deps=RAGAgentDependencies(
            session=session,
            redis=redis,
        ),
    )
    return agent_run.output
