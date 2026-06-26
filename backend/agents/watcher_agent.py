"""
THE WATCHER AGENT
=================
The ruthless boss, compassionate teacher, system guardian.
Runs continuously, observing, teaching, improving.

Three loops:
1. OBSERVATION (every 30s) - Monitor active tasks, detect stuck agents, watch costs
2. ANALYSIS (every 5 min) - Analyze performance, identify patterns, update memory
3. IMPROVEMENT (every 1h) - Refine scaffolds, update prompts, propose fixes
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import func
from models.base import SessionLocal
from models.task import Task, TaskStatus, TaskType
from services.evolving_memory import evolving_memory, EvolvingMemory, MemoryType, ConfidenceLevel
from services.model_router import model_router
from config import SETTINGS


class WatcherAgent:
    def __init__(self):
        self.last_analysis = datetime.utcnow() - timedelta(hours=1)
        self.last_improvement = datetime.utcnow() - timedelta(hours=1)
        self.agent_performance = {}

    async def run_observation_loop(self):
        """Main observation loop - runs every 30 seconds"""
        db = SessionLocal()
        try:
            # Check for stuck tasks
            stuck_tasks = self._find_stuck_tasks(db)
            for task in stuck_tasks:
                await self._handle_stuck_task(task, db)

            # Check for cost overruns
            cost_status = self._check_cost_status(db)
            if cost_status["over_limit"]:
                await self._handle_cost_overrun(cost_status, db)

            # Monitor active agents
            active = self._get_active_agents(db)
            if active:
                print(f"[WATCHER] {len(active)} agents active, cost: ${cost_status['total_today']:.4f}/{cost_status['limit']:.2f}")
        finally:
            db.close()

    async def run_analysis_loop(self):
        """Analysis loop - runs every 5 minutes"""
        now = datetime.utcnow()
        if (now - self.last_analysis).total_seconds() < 300:
            return

        self.last_analysis = now
        db = SessionLocal()
        try:
            await self._analyze_task_performance(db)
            await self._update_agent_performance(db)
        finally:
            db.close()

    async def run_improvement_loop(self):
        """Improvement loop - runs every hour"""
        now = datetime.utcnow()
        if (now - self.last_improvement).total_seconds() < 3600:
            return

        self.last_improvement = now
        db = SessionLocal()
        try:
            await self._refine_scaffolds(db)
            await self._propose_improvements(db)
            await self._generate_daily_report(db)
        finally:
            db.close()

    def _find_stuck_tasks(self, db) -> List[Task]:
        threshold = datetime.utcnow() - timedelta(minutes=10)
        return db.query(Task).filter(
            Task.status == TaskStatus.RUNNING,
            Task.started_at < threshold
        ).all()

    async def _handle_stuck_task(self, task: Task, db):
        await evolving_memory.log_execution(
            agent="watcher",
            task_type="stuck_detection",
            input_context={"task_id": task.id, "task_type": task.task_type.value},
            output_result={"action": "detected_stuck"},
            success=False,
            duration_seconds=0,
            cost=0
        )

        task.status = TaskStatus.FAILED
        task.error_message = "WATCHER: Task exceeded 10-minute timeout"
        db.commit()
        print(f"[WATCHER] Task {task.id} stuck. Marked failed for retry.")

    def _check_cost_status(self, db) -> Dict:
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())

        total_cost = db.query(func.sum(Task.ai_cost)).filter(
            Task.created_at >= today_start
        ).scalar() or 0

        limit = SETTINGS.max_daily_spend
        return {
            "total_today": float(total_cost),
            "limit": limit,
            "over_limit": float(total_cost) >= limit,
            "percent_used": (float(total_cost) / limit) * 100 if limit > 0 else 0
        }

    async def _handle_cost_overrun(self, status: Dict, db):
        non_essential = db.query(Task).filter(
            Task.status == TaskStatus.RUNNING,
            Task.task_type != TaskType.PUBLISH
        ).all()

        for task in non_essential:
            task.status = TaskStatus.CANCELLED
            task.error_message = f"WATCHER: Cost limit reached ({status['percent_used']:.0f}% used)"

        db.commit()
        print(f"[WATCHER] COST LIMIT REACHED: ${status['total_today']:.2f} / ${status['limit']:.2f}")

    def _get_active_agents(self, db) -> List[Dict]:
        active_tasks = db.query(Task).filter(
            Task.status == TaskStatus.RUNNING
        ).all()

        agents = {}
        for task in active_tasks:
            agent_name = task.task_type.value.split("_")[0]
            if agent_name not in agents:
                agents[agent_name] = []
            agents[agent_name].append(task.id)

        return [{"name": k, "task_ids": v} for k, v in agents.items()]

    async def _analyze_task_performance(self, db):
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_tasks = db.query(Task).filter(
            Task.created_at >= hour_ago
        ).all()

        if not recent_tasks:
            return

        total = len(recent_tasks)
        successful = sum(1 for t in recent_tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in recent_tasks if t.status == TaskStatus.FAILED)
        avg_cost = sum(t.ai_cost for t in recent_tasks) / total if total > 0 else 0

        performance = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "avg_cost": float(avg_cost),
        }

        await evolving_memory.log_execution(
            agent="watcher",
            task_type="performance_analysis",
            input_context={"timeframe": "1_hour"},
            output_result=performance,
            success=performance["success_rate"] > 0.8,
            duration_seconds=0,
            cost=0
        )

        print(f"[WATCHER] Performance: {performance['success_rate']*100:.0f}% success, ${avg_cost:.4f}/task")

    async def _update_agent_performance(self, db):
        day_ago = datetime.utcnow() - timedelta(days=1)
        recent_tasks = db.query(Task).filter(
            Task.created_at >= day_ago
        ).all()

        for task in recent_tasks:
            agent = task.task_type.value.split("_")[0]
            if agent not in self.agent_performance:
                self.agent_performance[agent] = {"total": 0, "success": 0, "cost": 0.0}

            self.agent_performance[agent]["total"] += 1
            self.agent_performance[agent]["cost"] += task.ai_cost

            if task.status == TaskStatus.COMPLETED:
                self.agent_performance[agent]["success"] += 1

    async def _refine_scaffolds(self, db):
        scaffolds = db.query(EvolvingMemory).filter(
            EvolvingMemory.memory_type == MemoryType.SCAFFOLD.value,
            EvolvingMemory.times_used >= 5
        ).all()

        for scaffold in scaffolds:
            await evolving_memory._refine_scaffold(scaffold)

        db.commit()

    async def _propose_improvements(self, db):
        for agent, stats in self.agent_performance.items():
            if stats["total"] >= 10:
                success_rate = stats["success"] / stats["total"]

                if success_rate < 0.7:
                    await self._propose_fix(agent, success_rate, db)

    async def _propose_fix(self, agent: str, success_rate: float, db):
        failures = db.query(Task).filter(
            Task.status == TaskStatus.FAILED,
            Task.created_at >= datetime.utcnow() - timedelta(days=3)
        ).all()

        if len(failures) < 3:
            return

        error_patterns = [f.error_message for f in failures if f.error_message][:5]

        try:
            analysis = await model_router.call(
                "analyze_agent_failures",
                f"""Agent {agent} is failing at {success_rate*100:.0f}% rate.

Recent error patterns:
{chr(10).join(error_patterns)}

Analyze and propose a fix. Output JSON:
{{
    "root_cause": "what's actually going wrong",
    "proposed_fix": "specific fix to implement",
    "file_to_modify": "which file to change",
    "modification_type": "prompt_update|code_change|config_change",
    "confidence": 0.8,
    "urgency": "high"
}}""",
                system_prompt="You are THE WATCHER analyzing agent failures. Be precise and actionable.",
                force_model="llama-70b",
                context={"estimated_value": 50}
            )

            proposal = analysis["content"]
            if isinstance(proposal, str):
                proposal = json.loads(proposal)

            if proposal.get("confidence", 0) > 0.6 and proposal.get("urgency") in ["high", "critical"]:
                await evolving_memory.propose_self_modification(
                    target_file=proposal.get("file_to_modify", "unknown"),
                    modification_type=proposal.get("modification_type", "prompt_update"),
                    current_content="(would read from file)",
                    reason=f"Agent {agent} failing at {success_rate*100:.0f}%: {proposal.get('root_cause', 'unknown')}",
                    proposed_change=proposal.get("proposed_fix", "")
                )

                print(f"[WATCHER] PROPOSED FIX: {proposal.get('file_to_modify')} - {proposal.get('proposed_fix', '')[:100]}")
        except Exception as e:
            print(f"[WATCHER] Fix proposal error: {e}")

    async def _generate_daily_report(self, db):
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_performance": self.agent_performance,
            "memory_stats": evolving_memory.get_memory_stats(),
            "total_cost_today": self._check_cost_status(db)["total_today"],
            "pending_improvements": db.query(func.count(EvolvingMemory.id))
                .filter(EvolvingMemory.memory_type == MemoryType.SELF_MODIFICATION.value).scalar() or 0
        }

        await evolving_memory.log_execution(
            agent="watcher",
            task_type="daily_report",
            input_context={},
            output_result=report,
            success=True,
            duration_seconds=0,
            cost=0
        )

        print(f"[WATCHER] Daily report generated. Cost: ${report['total_cost_today']:.2f}")
        return report


watcher_agent = WatcherAgent()
