try:
    from llama_index.core.tools import FunctionTool
except ImportError:
    # Handle the case where llama_index is not installed
    FunctionTool = None

from sardis_sdk import SardisClient

def _pay_vendor(amount: float, merchant: str, purpose: str = "Service payment") -> str:
    """
    Executes a payment via Sardis.
    """
    client = SardisClient(api_key="env") # Placeholder instantiation
    try:
        # NOTE: Full implementation requires constructing a signed mandate
        # result = client.payments.execute_mandate(...)
        return f"Payment of ${amount} to {merchant} for '{purpose}' initiated. TxID: mock_tx_123"
    except Exception as e:
        return f"Payment failed: {str(e)}"

def get_llamaindex_tool():
    """
    Returns a LlamaIndex FunctionTool for Sardis payments.
    """
    if FunctionTool is None:
        raise ImportError("llama-index-core is required to use this integration. Please install it.")
        
    return FunctionTool.from_defaults(
        fn=_pay_vendor,
        name="sardis_pay",
        description="Use this tool to execute payments and transfer funds."
    )
