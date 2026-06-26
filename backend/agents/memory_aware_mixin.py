"""
MEMORY-AWARE MIXIN
==================
All agents inherit this to get automatic memory integration.
"""

import time
from functools import wraps
from typing import Optional, List, Dict
from services.evolving_memory import evolving_memory, MemoryType


class MemoryAwareAgent:
    """Mixin that adds memory integration to any agent."""

    def _get_context_string(self, **kwargs) -> str:
        return " ".join(str(v) for v in kwargs.values() if v)

    def _load_relevant_memories(self, context: str, task_type: str) -> Dict:
        """Load memories relevant to current task"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context - can't await directly
                # Return empty for now, the async version will be used
                return {"patterns": [], "scaffolds": [], "anti_patterns": []}
            memories = loop.run_until_complete(
                evolving_memory.get_relevant_memories(
                    context=context,
                    memory_types=[MemoryType.PATTERN, MemoryType.SCAFFOLD, MemoryType.ANTI_PATTERN],
                    limit=5
                )
            )
            return {
                "patterns": [m for m in memories if m["type"] == "pattern"],
                "scaffolds": [m for m in memories if m["type"] == "scaffold"],
                "anti_patterns": [m for m in memories if m["type"] == "anti_pattern"]
            }
        except Exception as e:
            print(f"[Memory] Failed to load memories: {e}")
            return {"patterns": [], "scaffolds": [], "anti_patterns": []}

    async def _load_memories_async(self, context: str) -> Dict:
        """Async version of memory loading"""
        try:
            memories = await evolving_memory.get_relevant_memories(
                context=context,
                memory_types=[MemoryType.PATTERN, MemoryType.SCAFFOLD, MemoryType.ANTI_PATTERN],
                limit=5
            )
            return {
                "patterns": [m for m in memories if m["type"] == "pattern"],
                "scaffolds": [m for m in memories if m["type"] == "scaffold"],
                "anti_patterns": [m for m in memories if m["type"] == "anti_pattern"]
            }
        except Exception as e:
            print(f"[Memory] Failed to load memories: {e}")
            return {"patterns": [], "scaffolds": [], "anti_patterns": []}

    async def _log_execution(
        self,
        agent_name: str,
        task_type: str,
        input_ctx: Dict,
        output_result: Dict,
        success: bool,
        duration: float,
        cost: float,
        memories_used: List[str] = None
    ) -> str:
        """Log execution to evolving memory"""
        try:
            return await evolving_memory.log_execution(
                agent=agent_name,
                task_type=task_type,
                input_context=input_ctx,
                output_result=output_result,
                success=success,
                duration_seconds=duration,
                cost=cost,
                memories_used=memories_used
            )
        except Exception as e:
            print(f"[Memory] Failed to log execution: {e}")
            return "memory_log_failed"


def with_memory(agent_name: str, task_type: str):
    """
    Decorator that wraps agent methods with memory integration.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            context_parts = [str(a) for a in args if isinstance(a, (str, int, float))]
            context_parts.extend([str(v) for v in kwargs.values() if isinstance(v, (str, int, float))])
            context = " ".join(context_parts[:20])

            memories = await self._load_memories_async(context)
            kwargs["_memories"] = memories

            start_time = time.time()
            success = False
            result = None
            error = None

            try:
                result = await func(self, *args, **kwargs)
                success = True
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration = time.time() - start_time
                memory_ids_used = [m.get("memory_id") for m in memories.get("scaffolds", [])]

                await self._log_execution(
                    agent_name=agent_name,
                    task_type=task_type,
                    input_ctx={"context": context[:200]},
                    output_result={"success": success, "error": error, "result_type": str(type(result))},
                    success=success,
                    duration=duration,
                    cost=0.0,
                    memories_used=memory_ids_used
                )

            return result
        return wrapper
    return decorator
