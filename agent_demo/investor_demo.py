#!/usr/bin/env python3
"""
Sardis Investor Demo - Polished Terminal Presentation

This script provides a visually impressive demonstration of Sardis
for investor presentations. Features animated output, clear storytelling,
and real API interactions.

Usage:
    python agent_demo/investor_demo.py
    python agent_demo/investor_demo.py --interactive
"""

import sys
import time
import os
from decimal import Decimal
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, '.')

# ANSI Color codes for terminal styling
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    # Sardis brand colors (approximated for terminal)
    SARDIS = '\033[38;5;46m'  # Bright green
    GOLD = '\033[38;5;220m'


class DemoUI:
    """Terminal UI utilities for the demo."""
    
    def __init__(self, animate: bool = True):
        self.animate = animate
        self.terminal_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
    
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def sleep(self, seconds: float):
        """Sleep with animation toggle."""
        if self.animate:
            time.sleep(seconds)
    
    def type_text(self, text: str, delay: float = 0.02):
        """Simulate typing effect."""
        if self.animate:
            for char in text:
                print(char, end='', flush=True)
                time.sleep(delay)
            print()
        else:
            print(text)
    
    def print_banner(self):
        """Print Sardis ASCII art banner."""
        banner = f"""
{Colors.SARDIS}{Colors.BOLD}
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ███████╗ █████╗ ██████╗ ██████╗ ██╗███████╗              ║
    ║     ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║██╔════╝              ║
    ║     ███████╗███████║██████╔╝██║  ██║██║███████╗              ║
    ║     ╚════██║██╔══██║██╔══██╗██║  ██║██║╚════██║              ║
    ║     ███████║██║  ██║██║  ██║██████╔╝██║███████║              ║
    ║     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝              ║
    ║                                                               ║
    ║        {Colors.GOLD}AI Agent Payment Infrastructure{Colors.SARDIS}                       ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
{Colors.END}
"""
        print(banner)
    
    def print_header(self, title: str):
        """Print styled section header."""
        width = 60
        print(f"\n{Colors.SARDIS}{'═' * width}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.SARDIS}  ▸ {title}{Colors.END}")
        print(f"{Colors.SARDIS}{'═' * width}{Colors.END}\n")
    
    def print_step(self, step: int, total: int, title: str):
        """Print step indicator."""
        print(f"\n{Colors.CYAN}[{step}/{total}]{Colors.END} {Colors.BOLD}{title}{Colors.END}")
        print(f"{Colors.DIM}{'─' * 50}{Colors.END}\n")
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"  {Colors.GREEN}✓{Colors.END} {message}")
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"  {Colors.RED}✗{Colors.END} {message}")
    
    def print_info(self, label: str, value: str):
        """Print info line."""
        print(f"  {Colors.DIM}│{Colors.END} {label}: {Colors.BOLD}{value}{Colors.END}")
    
    def print_money(self, label: str, amount, currency: str = "USDC"):
        """Print money amount with styling."""
        print(f"  {Colors.DIM}│{Colors.END} {label}: {Colors.GREEN}${amount}{Colors.END} {Colors.DIM}{currency}{Colors.END}")
    
    def print_tx(self, tx_id: str, amount, purpose: str):
        """Print transaction in formatted way."""
        print(f"  {Colors.DIM}├─{Colors.END} {Colors.CYAN}{tx_id[:20]}...{Colors.END}")
        print(f"  {Colors.DIM}│  {Colors.END}Amount: {Colors.GREEN}${amount}{Colors.END}")
        print(f"  {Colors.DIM}│  {Colors.END}Purpose: {purpose}")
    
    def loading_animation(self, message: str, duration: float = 1.5):
        """Show loading animation."""
        if not self.animate:
            print(f"  {message}")
            return
        
        frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        end_time = time.time() + duration
        i = 0
        while time.time() < end_time:
            print(f"\r  {Colors.YELLOW}{frames[i % len(frames)]}{Colors.END} {message}", end='', flush=True)
            time.sleep(0.1)
            i += 1
        print(f"\r  {Colors.GREEN}✓{Colors.END} {message}")
    
    def progress_bar(self, current: int, total: int, label: str = ""):
        """Show progress bar."""
        width = 30
        filled = int(width * current / total)
        bar = '█' * filled + '░' * (width - filled)
        percent = int(100 * current / total)
        print(f"\r  {Colors.SARDIS}{bar}{Colors.END} {percent}% {label}", end='', flush=True)
        if current == total:
            print()
    
    def wait_for_key(self, message: str = "Press Enter to continue..."):
        """Wait for user input."""
        print(f"\n{Colors.DIM}{message}{Colors.END}")
        input()
    
    def print_divider(self):
        """Print section divider."""
        print(f"\n{Colors.DIM}{'─' * 60}{Colors.END}\n")
    
    def print_highlight_box(self, title: str, content: list[str]):
        """Print highlighted info box."""
        width = 56
        print(f"\n  {Colors.GOLD}┌{'─' * width}┐{Colors.END}")
        print(f"  {Colors.GOLD}│{Colors.END} {Colors.BOLD}{title.center(width - 2)}{Colors.END} {Colors.GOLD}│{Colors.END}")
        print(f"  {Colors.GOLD}├{'─' * width}┤{Colors.END}")
        for line in content:
            padding = width - 2 - len(line)
            print(f"  {Colors.GOLD}│{Colors.END} {line}{' ' * padding} {Colors.GOLD}│{Colors.END}")
        print(f"  {Colors.GOLD}└{'─' * width}┘{Colors.END}\n")


class InvestorDemo:
    """Main investor demonstration class."""
    
    def __init__(self, interactive: bool = False):
        self.ui = DemoUI(animate=True)
        self.interactive = interactive
        self.api_base = "http://localhost:8000"
        self._merchants = {}
    
    def check_api(self) -> bool:
        """Check if API is running."""
        import httpx
        try:
            response = httpx.get(f"{self.api_base}/api/v1/")
            if response.status_code == 200:
                data = response.json()
                self.ui.print_success(f"Connected to Sardis API v{data.get('version', '?')}")
                return True
        except Exception:
            pass
        self.ui.print_error("Cannot connect to API server")
        print(f"\n  Start the server with: {Colors.CYAN}uvicorn sardis_core.api.main:app --reload{Colors.END}")
        return False
    
    def setup_merchants(self):
        """Create demo merchants."""
        import httpx
        merchants = [
            ("GPU Cloud", "gpu_cloud", "compute"),
            ("Data API", "data_api", "data"),
            ("AI Services", "ai_services", "ai"),
        ]
        
        for name, key, category in merchants:
            try:
                response = httpx.post(
                    f"{self.api_base}/api/v1/merchants",
                    json={"name": name, "description": f"{name} provider", "category": category}
                )
                if response.status_code == 201:
                    self._merchants[key] = response.json().get('merchant_id')
            except:
                pass
    
    def create_agent(self, name: str, balance: float, limit_per_tx: float = 100.0) -> Optional[str]:
        """Create a demo agent and return its ID."""
        import httpx
        try:
            response = httpx.post(
                f"{self.api_base}/api/v1/agents",
                json={
                    "name": name,
                    "owner_id": "investor_demo",
                    "description": f"Demo agent: {name}",
                    "initial_balance": balance,
                    "limit_per_tx": limit_per_tx,
                    "limit_total": 10000.0
                }
            )
            if response.status_code == 201:
                return response.json()["agent"]["agent_id"]
        except Exception as e:
            self.ui.print_error(f"Failed to create agent: {e}")
        return None
    
    def run_intro(self):
        """Run intro sequence."""
        self.ui.clear_screen()
        self.ui.print_banner()
        
        self.ui.sleep(1)
        
        intro_text = """
    The future of AI is autonomous. But autonomous agents 
    need to pay for things: compute, data, APIs, and services.
    
    Today, there's no payment infrastructure designed for agents.
    
    Sardis changes that.
"""
        print(f"{Colors.DIM}{intro_text}{Colors.END}")
        
        if self.interactive:
            self.ui.wait_for_key()
        else:
            self.ui.sleep(3)
    
    def run_scenario_1(self):
        """Scenario 1: AI Shopping Agent."""
        from sardis_sdk import SardisClient
        
        self.ui.print_header("Scenario 1: AI Shopping Agent")
        
        print(f"""
  {Colors.BOLD}Use Case:{Colors.END} An AI agent autonomously purchases cloud compute
  time to run an LLM inference job.
  
  {Colors.DIM}This demonstrates pre-authorization holds, just like
  credit cards, but fully programmable.{Colors.END}
""")
        
        self.ui.sleep(1)
        
        # Step 1: Create agent
        self.ui.print_step(1, 5, "Creating AI Agent Wallet")
        self.ui.loading_animation("Generating wallet keypair...", 0.5)
        
        agent_id = self.create_agent("Shopping Agent", 500.0, 100.0)
        if not agent_id:
            return
        
        self.ui.print_success(f"Agent wallet created")
        self.ui.print_info("Agent ID", agent_id)
        self.ui.print_money("Initial Balance", "500.00")
        
        # Step 2: Agent evaluates purchase
        self.ui.print_step(2, 5, "Agent Evaluates GPU Purchase")
        
        self.ui.loading_animation("Querying GPU provider pricing...", 0.8)
        estimated_cost = Decimal("25.00")
        
        self.ui.print_info("Provider", "GPU Cloud (A100 instance)")
        self.ui.print_info("Estimated duration", "30 minutes")
        self.ui.print_money("Estimated cost", estimated_cost)
        
        # Step 3: Create hold
        self.ui.print_step(3, 5, "Creating Payment Hold")
        
        with SardisClient(base_url=self.api_base) as client:
            self.ui.loading_animation("Reserving funds...", 0.6)
            
            hold = client.create_hold(
                agent_id=agent_id,
                merchant_id=self._merchants.get("gpu_cloud", "gpu_provider"),
                amount=estimated_cost,
                purpose="GPU compute: A100 instance for LLM inference"
            )
            
            if hold.success:
                self.ui.print_success(f"Hold created: {hold.hold_id}")
                self.ui.print_money("Amount held", hold.amount)
                self.ui.print_info("Expires", str(hold.expires_at)[:19])
                
                # Step 4: Simulate job
                self.ui.print_step(4, 5, "Running GPU Job")
                
                print(f"  {Colors.DIM}Simulating job execution...{Colors.END}")
                for i in range(1, 11):
                    self.ui.progress_bar(i, 10, "GPU utilization")
                    self.ui.sleep(0.2)
                
                actual_cost = Decimal("22.50")
                self.ui.print_success("Job completed successfully")
                self.ui.print_money("Actual cost", actual_cost)
                self.ui.print_money("Savings", estimated_cost - actual_cost)
                
                # Step 5: Capture payment
                self.ui.print_step(5, 5, "Capturing Payment")
                
                self.ui.loading_animation("Finalizing transaction...", 0.5)
                
                result = client.capture_hold(hold.hold_id, actual_cost)
                
                if result.success:
                    self.ui.print_success("Payment captured!")
                    self.ui.print_info("Transaction ID", result.transaction.tx_id)
                    self.ui.print_money("Amount charged", result.transaction.amount)
                    self.ui.print_money("Fee", result.transaction.fee)
                    
                    # Final balance
                    wallet = client.get_wallet_info(agent_id)
                    
                    self.ui.print_highlight_box("Transaction Complete", [
                        f"Agent started with: $500.00 USDC",
                        f"Amount spent: ${actual_cost} + ${result.transaction.fee} fee",
                        f"Final balance: ${wallet.balance} USDC",
                        "",
                        "✓ Fully autonomous payment",
                        "✓ No human approval required",
                        "✓ Verifiable on blockchain",
                    ])
    
    def run_scenario_2(self):
        """Scenario 2: Agent-to-Agent Marketplace."""
        from sardis_sdk import SardisClient
        
        self.ui.print_header("Scenario 2: Agent-to-Agent Economy")
        
        print(f"""
  {Colors.BOLD}Use Case:{Colors.END} Two AI agents transact directly. One provides
  document analysis services, the other pays for it.
  
  {Colors.DIM}This demonstrates the future: agents with economic agency,
  trading services in a global marketplace.{Colors.END}
""")
        
        self.ui.sleep(1)
        
        # Create two agents
        self.ui.print_step(1, 4, "Creating Agent Marketplace")
        
        self.ui.loading_animation("Creating Provider Agent...", 0.4)
        provider_id = self.create_agent("Document Analyst", 0.0, 1000.0)
        self.ui.print_success(f"Provider Agent: {provider_id}")
        self.ui.print_info("Service", "Document Analysis")
        self.ui.print_money("Starting balance", "0.00")
        
        self.ui.loading_animation("Creating Buyer Agent...", 0.4)
        buyer_id = self.create_agent("Research Assistant", 200.0, 100.0)
        self.ui.print_success(f"Buyer Agent: {buyer_id}")
        self.ui.print_info("Task", "Analyze 50-page research paper")
        self.ui.print_money("Starting balance", "200.00")
        
        if not provider_id or not buyer_id:
            return
        
        with SardisClient(base_url=self.api_base) as client:
            # Get provider wallet for payment
            provider_wallet = client.get_wallet_info(provider_id)
            
            # Agent negotiation
            self.ui.print_step(2, 4, "Agent Negotiation")
            
            self.ui.loading_animation("Agents negotiating price...", 0.8)
            price = Decimal("15.00")
            
            print(f"\n  {Colors.CYAN}[Buyer Agent]{Colors.END}: I need to analyze a research paper")
            self.ui.sleep(0.5)
            print(f"  {Colors.GOLD}[Provider Agent]{Colors.END}: My rate is $15.00 for documents up to 100 pages")
            self.ui.sleep(0.5)
            print(f"  {Colors.CYAN}[Buyer Agent]{Colors.END}: Agreed. Initiating payment...")
            
            # Payment
            self.ui.print_step(3, 4, "Payment Transfer")
            
            self.ui.loading_animation("Processing agent-to-agent payment...", 0.6)
            
            result = client.pay(
                agent_id=buyer_id,
                amount=price,
                recipient_wallet_id=provider_wallet.wallet_id,
                purpose="Document analysis: research paper (50 pages)"
            )
            
            if result.success:
                self.ui.print_success("Payment successful!")
                self.ui.print_tx(
                    result.transaction.tx_id,
                    result.transaction.amount,
                    "Document analysis service"
                )
            
            # Service delivery simulation
            self.ui.print_step(4, 4, "Service Delivery")
            
            print(f"\n  {Colors.GOLD}[Provider Agent]{Colors.END}: Payment received. Analyzing document...")
            
            for i in range(1, 11):
                self.ui.progress_bar(i, 10, "Analysis progress")
                self.ui.sleep(0.15)
            
            print(f"  {Colors.GOLD}[Provider Agent]{Colors.END}: Analysis complete. Sending results...")
            self.ui.sleep(0.5)
            print(f"  {Colors.CYAN}[Buyer Agent]{Colors.END}: Results received. Thank you!")
            
            # Final state
            provider_wallet = client.get_wallet_info(provider_id)
            buyer_wallet = client.get_wallet_info(buyer_id)
            
            self.ui.print_highlight_box("Agent Economy Complete", [
                f"Provider Agent earned: ${provider_wallet.balance}",
                f"Buyer Agent remaining: ${buyer_wallet.balance}",
                "",
                "✓ Fully autonomous transaction",
                "✓ Agent-to-agent payment",
                "✓ Instant settlement",
                "✓ No intermediary required",
            ])
    
    def run_scenario_3(self):
        """Scenario 3: Micropayments at Scale."""
        from sardis_sdk import SardisClient
        
        self.ui.print_header("Scenario 3: Micropayments at Scale")
        
        print(f"""
  {Colors.BOLD}Use Case:{Colors.END} An AI agent makes rapid micropayments for
  real-time data feeds and API calls.
  
  {Colors.DIM}Traditional payment systems can't handle $0.001 transactions.
  Sardis enables true pay-per-use models.{Colors.END}
""")
        
        self.ui.sleep(1)
        
        # Create agent
        self.ui.print_step(1, 3, "Setting Up Data Agent")
        
        agent_id = self.create_agent("Data Aggregator", 10.0, 1.0)
        if not agent_id:
            return
        
        self.ui.print_success(f"Agent created: {agent_id}")
        self.ui.print_money("Balance", "10.00")
        
        # Simulate rapid payments
        self.ui.print_step(2, 3, "Real-Time Data Acquisition")
        
        data_sources = [
            ("Weather API", Decimal("0.01")),
            ("Stock Feed", Decimal("0.02")),
            ("News Stream", Decimal("0.01")),
            ("Satellite Data", Decimal("0.05")),
            ("Traffic Data", Decimal("0.01")),
        ]
        
        with SardisClient(base_url=self.api_base) as client:
            total_spent = Decimal("0")
            tx_count = 0
            
            merchant_id = self._merchants.get("data_api", "data_provider")
            
            for source, cost in data_sources:
                print(f"\n  {Colors.DIM}Fetching:{Colors.END} {source}")
                self.ui.loading_animation(f"Paying ${cost}...", 0.3)
                
                result = client.pay(
                    agent_id=agent_id,
                    amount=cost,
                    merchant_id=merchant_id,
                    purpose=f"API call: {source}"
                )
                
                if result.success:
                    total_spent += cost
                    tx_count += 1
                    self.ui.print_success(f"${cost} → {source}")
            
            # Summary
            self.ui.print_step(3, 3, "Micropayment Summary")
            
            wallet = client.get_wallet_info(agent_id)
            
            self.ui.print_highlight_box("Micropayment Statistics", [
                f"Transactions: {tx_count}",
                f"Total spent: ${total_spent}",
                f"Average: ${total_spent / tx_count:.4f} per call",
                f"Remaining balance: ${wallet.balance}",
                "",
                "✓ Sub-cent transactions supported",
                "✓ Instant settlement",
                "✓ No minimum transaction size",
            ])
    
    def run_summary(self):
        """Show final summary."""
        self.ui.print_header("Why Sardis?")
        
        print(f"""
  {Colors.BOLD}The Agent Economy Needs Payment Rails{Colors.END}
  
  {Colors.SARDIS}►{Colors.END} AI agents are becoming economically autonomous
  {Colors.SARDIS}►{Colors.END} Traditional payments don't work for agents
  {Colors.SARDIS}►{Colors.END} Micropayments require new infrastructure
  {Colors.SARDIS}►{Colors.END} Agent-to-agent commerce is emerging
  
  {Colors.BOLD}Sardis Provides:{Colors.END}
  
  {Colors.GREEN}✓{Colors.END} Instant wallet creation (< 1 second)
  {Colors.GREEN}✓{Colors.END} Programmable spending limits
  {Colors.GREEN}✓{Colors.END} Pre-authorization & holds
  {Colors.GREEN}✓{Colors.END} Micropayments (no minimum)
  {Colors.GREEN}✓{Colors.END} Agent-to-agent transfers
  {Colors.GREEN}✓{Colors.END} Blockchain verification
  {Colors.GREEN}✓{Colors.END} Developer-first API
  
""")
        
        self.ui.print_highlight_box("Market Opportunity", [
            "• AI agent market: $XX billion by 2028",
            "• Agent payment transactions: Zero infrastructure today",
            "• Sardis: First mover in agent payments",
            "",
            "The Stripe for AI Agents",
        ])
    
    def run(self):
        """Run the full demo."""
        self.run_intro()
        
        if not self.check_api():
            return
        
        self.setup_merchants()
        
        if self.interactive:
            self.ui.wait_for_key()
        
        self.run_scenario_1()
        
        if self.interactive:
            self.ui.wait_for_key()
        else:
            self.ui.sleep(2)
        
        self.run_scenario_2()
        
        if self.interactive:
            self.ui.wait_for_key()
        else:
            self.ui.sleep(2)
        
        self.run_scenario_3()
        
        if self.interactive:
            self.ui.wait_for_key()
        else:
            self.ui.sleep(2)
        
        self.run_summary()
        
        print(f"\n{Colors.DIM}Demo complete. Visit http://localhost:3000 for dashboard.{Colors.END}\n")


def main():
    interactive = "--interactive" in sys.argv or "-i" in sys.argv
    demo = InvestorDemo(interactive=interactive)
    demo.run()


if __name__ == "__main__":
    main()

