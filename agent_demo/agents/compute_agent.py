"""
Compute Agent - An agent that pays for GPU/inference resources.

This agent demonstrates:
- Paying for compute resources (GPU time, inference credits)
- Pre-authorization holds for estimated usage
- Metered billing with final capture
- Service authorization for compute providers
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import time

from sardis_sdk import SardisClient, PaymentResult, HoldResult


@dataclass
class ComputeJob:
    """A compute job submitted by the agent."""
    job_id: str
    provider_id: str
    resource_type: str  # "gpu", "cpu", "inference"
    estimated_cost: Decimal
    actual_cost: Optional[Decimal] = None
    hold_id: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed


class ComputeAgent:
    """
    An agent that purchases compute resources for AI workloads.
    
    This agent can:
    - Estimate costs for compute jobs
    - Create holds for estimated usage
    - Track job execution
    - Pay for actual usage on completion
    
    Example workflow:
        1. Agent estimates job cost
        2. Creates a hold for the estimated amount
        3. Submits job to compute provider
        4. On completion, captures actual cost (may be less than hold)
        5. If job fails, voids the hold
    
    Usage:
        ```python
        agent = ComputeAgent("agent_compute_001", sardis_client)
        
        # Submit a GPU job
        job = await agent.submit_job(
            provider_id="gpu_provider_1",
            resource_type="gpu",
            estimated_cost=Decimal("5.00"),
            job_params={"model": "llama2", "tokens": 1000}
        )
        
        # Complete the job with actual cost
        result = await agent.complete_job(job.job_id, actual_cost=Decimal("4.50"))
        ```
    """
    
    def __init__(self, agent_id: str, client: SardisClient):
        """
        Initialize the compute agent.
        
        Args:
            agent_id: This agent's ID
            client: Sardis SDK client
        """
        self.agent_id = agent_id
        self.client = client
        self._jobs: dict[str, ComputeJob] = {}
        self._job_counter = 0
    
    def get_balance(self) -> Decimal:
        """Get current wallet balance."""
        wallet = self.client.get_wallet_info(self.agent_id)
        return wallet.balance
    
    def authorize_provider(self, provider_id: str) -> bool:
        """
        Pre-authorize a compute provider.
        
        This reduces risk scoring for payments to this provider.
        """
        return self.client.authorize_service(self.agent_id, provider_id)
    
    def estimate_cost(
        self,
        resource_type: str,
        duration_seconds: int,
        tier: str = "standard"
    ) -> Decimal:
        """
        Estimate cost for a compute job.
        
        Args:
            resource_type: Type of resource (gpu, cpu, inference)
            duration_seconds: Expected job duration
            tier: Resource tier (standard, premium)
            
        Returns:
            Estimated cost in USDC
        """
        # Pricing per second (example rates)
        rates = {
            "gpu": {"standard": Decimal("0.001"), "premium": Decimal("0.005")},
            "cpu": {"standard": Decimal("0.0001"), "premium": Decimal("0.0005")},
            "inference": {"standard": Decimal("0.0005"), "premium": Decimal("0.002")},
        }
        
        rate = rates.get(resource_type, {}).get(tier, Decimal("0.001"))
        cost = rate * duration_seconds
        
        # Add 20% buffer for estimation
        return (cost * Decimal("1.2")).quantize(Decimal("0.01"))
    
    def submit_job(
        self,
        provider_id: str,
        resource_type: str,
        estimated_cost: Decimal,
        job_params: Optional[dict] = None
    ) -> ComputeJob:
        """
        Submit a compute job with pre-authorized payment.
        
        Creates a hold for the estimated cost, which will be
        captured (or partially captured) when the job completes.
        
        Args:
            provider_id: Compute provider merchant ID
            resource_type: Type of resource needed
            estimated_cost: Estimated job cost
            job_params: Optional job parameters
            
        Returns:
            ComputeJob with hold information
        """
        # Generate job ID
        self._job_counter += 1
        job_id = f"job_{self.agent_id}_{self._job_counter}"
        
        # Create hold for estimated cost
        hold_result = self.client.create_hold(
            agent_id=self.agent_id,
            merchant_id=provider_id,
            amount=estimated_cost,
            purpose=f"Compute job {job_id}: {resource_type}"
        )
        
        if not hold_result.success:
            job = ComputeJob(
                job_id=job_id,
                provider_id=provider_id,
                resource_type=resource_type,
                estimated_cost=estimated_cost,
                status="failed"
            )
            self._jobs[job_id] = job
            raise Exception(f"Failed to create hold: {hold_result.error}")
        
        job = ComputeJob(
            job_id=job_id,
            provider_id=provider_id,
            resource_type=resource_type,
            estimated_cost=estimated_cost,
            hold_id=hold_result.hold_id,
            status="running"
        )
        self._jobs[job_id] = job
        
        print(f"[ComputeAgent] Job {job_id} submitted")
        print(f"  Provider: {provider_id}")
        print(f"  Resource: {resource_type}")
        print(f"  Estimated cost: ${estimated_cost}")
        print(f"  Hold ID: {hold_result.hold_id}")
        
        return job
    
    def complete_job(
        self,
        job_id: str,
        actual_cost: Decimal
    ) -> PaymentResult:
        """
        Complete a job and capture payment.
        
        Args:
            job_id: Job to complete
            actual_cost: Actual cost incurred
            
        Returns:
            PaymentResult from the capture
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != "running":
            raise ValueError(f"Job {job_id} is not running (status: {job.status})")
        
        if not job.hold_id:
            raise ValueError(f"Job {job_id} has no hold")
        
        # Capture the hold with actual cost
        result = self.client.capture_hold(job.hold_id, actual_cost)
        
        if result.success:
            job.status = "completed"
            job.actual_cost = actual_cost
            
            savings = job.estimated_cost - actual_cost
            print(f"[ComputeAgent] Job {job_id} completed")
            print(f"  Actual cost: ${actual_cost}")
            if savings > 0:
                print(f"  Savings: ${savings} (under estimate)")
        else:
            job.status = "failed"
            print(f"[ComputeAgent] Job {job_id} capture failed: {result.error}")
        
        return result
    
    def cancel_job(self, job_id: str) -> HoldResult:
        """
        Cancel a running job and void the hold.
        
        Args:
            job_id: Job to cancel
            
        Returns:
            HoldResult from voiding
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != "running":
            raise ValueError(f"Job {job_id} is not running")
        
        if not job.hold_id:
            raise ValueError(f"Job {job_id} has no hold")
        
        result = self.client.void_hold(job.hold_id)
        
        if result.success:
            job.status = "cancelled"
            print(f"[ComputeAgent] Job {job_id} cancelled, hold voided")
        
        return result
    
    def get_job(self, job_id: str) -> Optional[ComputeJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
    
    def list_jobs(self, status: Optional[str] = None) -> list[ComputeJob]:
        """List jobs, optionally filtered by status."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs
    
    def get_total_spent(self) -> Decimal:
        """Get total amount spent on completed jobs."""
        return sum(
            j.actual_cost or Decimal("0")
            for j in self._jobs.values()
            if j.status == "completed"
        )


# Example usage
def demo_compute_agent():
    """Demonstrate the compute agent."""
    from sardis_sdk import SardisClient
    
    print("=== Compute Agent Demo ===\n")
    
    with SardisClient() as client:
        agent = ComputeAgent("agent_compute_demo", client)
        
        # Check balance
        balance = agent.get_balance()
        print(f"Starting balance: ${balance}\n")
        
        # Authorize a provider
        agent.authorize_provider("gpu_provider_1")
        
        # Estimate a job
        estimated = agent.estimate_cost("gpu", duration_seconds=60, tier="standard")
        print(f"Estimated cost for 60s GPU job: ${estimated}\n")
        
        # Submit the job
        try:
            job = agent.submit_job(
                provider_id="gpu_provider_1",
                resource_type="gpu",
                estimated_cost=estimated,
                job_params={"model": "llama2", "max_tokens": 1000}
            )
            
            # Simulate job running
            print("\n[Simulating job execution...]\n")
            time.sleep(1)
            
            # Complete with actual cost (less than estimate)
            actual = Decimal("0.05")
            result = agent.complete_job(job.job_id, actual)
            
            if result.success:
                print(f"\nTransaction ID: {result.transaction.tx_id}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        # Final balance
        print(f"\nFinal balance: ${agent.get_balance()}")
        print(f"Total spent: ${agent.get_total_spent()}")


if __name__ == "__main__":
    demo_compute_agent()

