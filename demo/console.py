"""Colorized console output for demos."""

from enum import Enum
from typing import Optional


class Color(str, Enum):
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Regular colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Backgrounds
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class Console:
    """Pretty console output for demos."""
    
    SARDIS_LOGO = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   ███████╗ █████╗ ██████╗ ██████╗ ██╗███████╗                ║
    ║   ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║██╔════╝                ║
    ║   ███████╗███████║██████╔╝██║  ██║██║███████╗                ║
    ║   ╚════██║██╔══██║██╔══██╗██║  ██║██║╚════██║                ║
    ║   ███████║██║  ██║██║  ██║██████╔╝██║███████║                ║
    ║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝                ║
    ║                                                               ║
    ║   Programmable Stablecoin Payment Network for AI Agents       ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def _print(self, message: str, color: Optional[Color] = None, bold: bool = False):
        """Print with optional color and formatting."""
        if not self.verbose:
            return
        
        prefix = ""
        suffix = Color.RESET.value
        
        if bold:
            prefix += Color.BOLD.value
        if color:
            prefix += color.value
        
        print(f"{prefix}{message}{suffix}")
    
    def logo(self):
        """Print the Sardis logo."""
        self._print(self.SARDIS_LOGO, Color.CYAN)
    
    def header(self, text: str):
        """Print a section header."""
        width = 60
        border = "═" * width
        padded = text.center(width - 2)
        
        self._print(f"\n╔{border}╗", Color.BRIGHT_BLUE)
        self._print(f"║ {padded} ║", Color.BRIGHT_BLUE, bold=True)
        self._print(f"╚{border}╝", Color.BRIGHT_BLUE)
    
    def subheader(self, text: str):
        """Print a sub-section header."""
        self._print(f"\n▸ {text}", Color.BRIGHT_CYAN, bold=True)
        self._print("─" * 50, Color.DIM)
    
    def info(self, message: str):
        """Print info message."""
        self._print(f"ℹ️  {message}", Color.BRIGHT_WHITE)
    
    def success(self, message: str):
        """Print success message."""
        self._print(f"✅ {message}", Color.BRIGHT_GREEN)
    
    def warning(self, message: str):
        """Print warning message."""
        self._print(f"⚠️  {message}", Color.BRIGHT_YELLOW)
    
    def error(self, message: str):
        """Print error message."""
        self._print(f"❌ {message}", Color.BRIGHT_RED)
    
    def money(self, amount: str, label: str = ""):
        """Print money amount with special formatting."""
        if label:
            self._print(f"💰 {label}: ${amount} USDC", Color.BRIGHT_GREEN)
        else:
            self._print(f"💰 ${amount} USDC", Color.BRIGHT_GREEN)
    
    def transaction(self, tx_id: str, amount: str, status: str):
        """Print transaction details."""
        status_color = Color.BRIGHT_GREEN if status == "completed" else Color.BRIGHT_RED
        
        self._print(f"\n📋 Transaction Details:", Color.BRIGHT_MAGENTA, bold=True)
        self._print(f"   ID: {tx_id}", Color.DIM)
        self._print(f"   Amount: ${amount} USDC", Color.BRIGHT_WHITE)
        print(f"   Status: {status_color.value}{status}{Color.RESET.value}")
    
    def agent_info(self, agent_type: str, agent_id: str):
        """Print agent information."""
        emoji = {
            "data_buyer": "📊",
            "automation": "🤖",
            "budget_optimizer": "💹",
            "shopping": "🛒",
        }.get(agent_type, "🤖")
        
        self._print(f"\n{emoji} Agent: {agent_type}", Color.BRIGHT_CYAN, bold=True)
        self._print(f"   ID: {agent_id}", Color.DIM)
    
    def wallet_status(
        self,
        balance: str,
        spent: str,
        remaining: str,
        currency: str = "USDC"
    ):
        """Print wallet status."""
        self._print(f"\n💳 Wallet Status:", Color.BRIGHT_YELLOW, bold=True)
        self._print(f"   Balance: ${balance} {currency}", Color.BRIGHT_GREEN)
        self._print(f"   Spent: ${spent} {currency}", Color.BRIGHT_WHITE)
        self._print(f"   Remaining Limit: ${remaining} {currency}", Color.BRIGHT_CYAN)
    
    def step(self, number: int, description: str):
        """Print a step in a sequence."""
        self._print(f"\n[{number}] {description}", Color.BRIGHT_MAGENTA, bold=True)
    
    def thinking(self, message: str = "Agent thinking..."):
        """Print thinking indicator."""
        self._print(f"🧠 {message}", Color.BRIGHT_YELLOW)
    
    def action(self, tool_name: str, args: str = ""):
        """Print agent action."""
        self._print(f"🔧 Using tool: {tool_name}", Color.BRIGHT_BLUE)
        if args:
            self._print(f"   Args: {args}", Color.DIM)
    
    def response(self, message: str):
        """Print agent response."""
        self._print(f"\n📝 Agent Response:", Color.BRIGHT_GREEN, bold=True)
        # Indent each line of the response
        for line in message.split("\n"):
            self._print(f"   {line}", Color.WHITE)
    
    def divider(self):
        """Print a divider line."""
        self._print("\n" + "─" * 60, Color.DIM)
    
    def countdown(self, seconds: int = 3, message: str = "Starting in"):
        """Print countdown (doesn't actually wait)."""
        import time
        for i in range(seconds, 0, -1):
            self._print(f"\r{message} {i}...", Color.BRIGHT_YELLOW)
            time.sleep(1)
        print()
    
    def progress(self, current: int, total: int, label: str = "Progress"):
        """Print progress bar."""
        width = 40
        filled = int(width * current / total)
        bar = "█" * filled + "░" * (width - filled)
        percent = int(100 * current / total)
        
        print(f"\r{Color.BRIGHT_CYAN.value}{label}: [{bar}] {percent}%{Color.RESET.value}", end="")
        if current == total:
            print()


# Singleton instance
console = Console()

