"""Base agent class for Sardis demonstrations."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional
import os

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from sardis_sdk import SardisClient


class BaseAgent(ABC):
    """
    Abstract base class for all Sardis demo agents.
    
    Provides common functionality for:
    - Sardis client management
    - LLM initialization
    - Agent execution
    """
    
    def __init__(
        self,
        agent_id: str,
        sardis_url: str = "http://localhost:8000",
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        verbose: bool = True
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_id: The Sardis agent ID
            sardis_url: URL of the Sardis API
            openai_api_key: OpenAI API key
            model: LLM model to use
            temperature: LLM temperature
            verbose: Whether to print verbose output
        """
        self.agent_id = agent_id
        self.sardis_url = sardis_url
        self.verbose = verbose
        
        # Initialize Sardis client
        self.sardis_client = SardisClient(base_url=sardis_url)
        
        # Initialize LLM
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
        
        # Setup agent (to be implemented by subclasses)
        self._setup_agent()
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the type of agent."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent type."""
        pass
    
    @abstractmethod
    def _get_tools(self) -> list:
        """Return the tools available to this agent."""
        pass
    
    def _setup_agent(self):
        """Set up the LangChain agent."""
        tools = self._get_tools()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt
        )
        
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=self.verbose,
            handle_parsing_errors=True,
            max_iterations=10
        )
    
    def execute(self, task: str) -> str:
        """
        Execute a task.
        
        Args:
            task: Natural language description of the task
            
        Returns:
            Agent's response
        """
        result = self.executor.invoke({"input": task})
        return result.get("output", "No response from agent")
    
    def get_balance(self) -> Decimal:
        """Get current wallet balance."""
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return wallet.balance
        except Exception as e:
            return Decimal("0")
    
    def get_wallet_status(self) -> dict:
        """Get full wallet status."""
        try:
            wallet = self.sardis_client.get_wallet_info(self.agent_id)
            return {
                "balance": wallet.balance,
                "currency": wallet.currency,
                "limit_per_tx": wallet.limit_per_tx,
                "limit_total": wallet.limit_total,
                "spent_total": wallet.spent_total,
                "remaining_limit": wallet.remaining_limit,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def close(self):
        """Close the Sardis client connection."""
        self.sardis_client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()

