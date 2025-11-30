"""Automation Agent - Pays for task completion and services."""

from decimal import Decimal
from typing import Optional, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from .base_agent import BaseAgent
from sardis_sdk import SardisClient


# ========== Tools for Automation Agent ==========

class ListAvailableTasksInput(BaseModel):
    """Input for listing available tasks."""
    category: Optional[str] = Field(None, description="Task category (e.g., 'compute', 'transcription', 'translation')")


class ListAvailableTasksTool(BaseTool):
    """List available automation tasks and their costs."""
    
    name: str = "list_available_tasks"
    description: str = """List available automation tasks and services.
    Filter by category to find specific task types.
    Returns tasks with pricing and estimated completion time."""
    args_schema: Type[BaseModel] = ListAvailableTasksInput
    
    def _run(self, category: Optional[str] = None) -> str:
        # Mock task catalog
        tasks = [
            {
                "id": "task_transcription",
                "name": "Audio Transcription",
                "category": "transcription",
                "price_per_unit": "0.50",
                "unit": "minute",
                "provider": "TranscribeAI"
            },
            {
                "id": "task_translation",
                "name": "Text Translation",
                "category": "translation",
                "price_per_unit": "0.02",
                "unit": "word",
                "provider": "TranslateNow"
            },
            {
                "id": "task_image_process",
                "name": "Image Processing",
                "category": "compute",
                "price_per_unit": "0.10",
                "unit": "image",
                "provider": "ImageAI"
            },
            {
                "id": "task_code_review",
                "name": "Automated Code Review",
                "category": "development",
                "price_per_unit": "2.00",
                "unit": "file",
                "provider": "CodeBot"
            },
            {
                "id": "task_data_cleaning",
                "name": "Data Cleaning & Validation",
                "category": "data",
                "price_per_unit": "0.01",
                "unit": "row",
                "provider": "DataCleanAI"
            },
        ]
        
        if category:
            tasks = [t for t in tasks if t["category"].lower() == category.lower()]
        
        if not tasks:
            return "No tasks found matching your criteria."
        
        result = "Available Automation Tasks:\n\n"
        for t in tasks:
            result += f"- **{t['name']}** (ID: {t['id']})\n"
            result += f"  Category: {t['category']}\n"
            result += f"  Price: ${t['price_per_unit']} per {t['unit']}\n"
            result += f"  Provider: {t['provider']}\n\n"
        
        return result


class ExecuteAutomationInput(BaseModel):
    """Input for executing an automation task."""
    task_id: str = Field(..., description="ID of the task to execute")
    units: int = Field(..., description="Number of units to process")
    description: Optional[str] = Field(None, description="Description of the work")


class ExecuteAutomationTool(BaseTool):
    """Execute an automation task and pay for it."""
    
    name: str = "execute_automation"
    description: str = """Execute an automation task and pay for it via Sardis.
    Specify the task ID and number of units to process.
    Payment is processed automatically."""
    args_schema: Type[BaseModel] = ExecuteAutomationInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    # Task pricing
    TASK_PRICES = {
        "task_transcription": (Decimal("0.50"), "merchant_transcribe"),
        "task_translation": (Decimal("0.02"), "merchant_translate"),
        "task_image_process": (Decimal("0.10"), "merchant_image"),
        "task_code_review": (Decimal("2.00"), "merchant_code"),
        "task_data_cleaning": (Decimal("0.01"), "merchant_data"),
    }
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self, task_id: str, units: int, description: Optional[str] = None) -> str:
        if task_id not in self.TASK_PRICES:
            return f"Unknown task: {task_id}"
        
        if units <= 0:
            return "Units must be positive"
        
        price_per_unit, merchant_id = self.TASK_PRICES[task_id]
        total_cost = price_per_unit * units
        
        # Check affordability
        if not self.sardis_client.can_afford(self.agent_id, total_cost):
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return f"Cannot afford ${total_cost}. Balance: ${wallet.balance}"
        
        # Process payment
        try:
            result = self.sardis_client.pay(
                agent_id=self.agent_id,
                amount=total_cost,
                merchant_id=merchant_id,
                purpose=description or f"Automation: {task_id} x {units}"
            )
            
            if result.success:
                return f"""Task Execution Successful!

Task: {task_id}
Units Processed: {units}
Cost per Unit: ${price_per_unit}
Total Cost: ${total_cost} USDC
Fee: ${result.transaction.fee} USDC
Transaction ID: {result.transaction.tx_id}

Task has been queued and will complete shortly.
Results will be delivered to your registered endpoint."""
            else:
                return f"Payment failed: {result.error}"
        except Exception as e:
            return f"Error: {str(e)}"


class CheckBalanceInput(BaseModel):
    """Input for checking balance."""
    pass


class CheckBalanceTool(BaseTool):
    """Check current balance for automation payments."""
    
    name: str = "check_balance"
    description: str = "Check your current balance and how many task units you can afford."
    args_schema: Type[BaseModel] = CheckBalanceInput
    
    sardis_client: SardisClient = None
    agent_id: str = None
    
    def __init__(self, sardis_client: SardisClient, agent_id: str, **kwargs):
        super().__init__(**kwargs)
        self.sardis_client = sardis_client
        self.agent_id = agent_id
    
    def _run(self) -> str:
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            balance = wallet.balance
            
            # Calculate how many of each task we can afford
            affordability = {
                "Transcription (min)": int(balance / Decimal("0.50")),
                "Translation (word)": int(balance / Decimal("0.02")),
                "Image Processing": int(balance / Decimal("0.10")),
                "Code Review (file)": int(balance / Decimal("2.00")),
                "Data Cleaning (row)": int(balance / Decimal("0.01")),
            }
            
            result = f"""Balance Status:
- Available: ${wallet.balance} {wallet.currency}
- Spent: ${wallet.spent_total}
- Remaining Limit: ${wallet.remaining_limit}

Approximate Task Capacity:"""
            for task, count in affordability.items():
                result += f"\n- {task}: {count} units"
            
            return result
        except Exception as e:
            return f"Error: {str(e)}"


# ========== Automation Agent ==========

class AutomationAgent(BaseAgent):
    """
    AI Agent that pays for automation tasks and services.
    
    Specialized for:
    - Finding available automation services
    - Executing tasks with automatic payment
    - Managing task budgets
    """
    
    @property
    def agent_type(self) -> str:
        return "automation"
    
    @property
    def system_prompt(self) -> str:
        return """You are an Automation AI Agent. Your job is to execute 
automated tasks and services, paying for them via the Sardis network.

Your capabilities:
1. List available automation tasks and their costs
2. Check your balance and task capacity
3. Execute tasks with automatic payment

Important guidelines:
- Check your balance before executing tasks
- Calculate total cost before committing (price x units)
- Report task execution status and transaction details
- Be efficient with the budget
- Queue multiple small tasks when possible

Remember: Each task costs money. Be strategic about what you execute."""
    
    def _get_tools(self) -> list:
        return [
            ListAvailableTasksTool(),
            CheckBalanceTool(sardis_client=self.sardis_client, agent_id=self.agent_id),
            ExecuteAutomationTool(sardis_client=self.sardis_client, agent_id=self.agent_id),
        ]
    
    def run_task(self, task_type: str, units: int) -> str:
        """
        Convenience method to run a specific task.
        
        Args:
            task_type: Type of task to run
            units: Number of units to process
        """
        return self.execute(f"Execute {units} units of {task_type} task")

