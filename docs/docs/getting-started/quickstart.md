# Quickstart

Get your first agent payment running in 5 minutes.

## Prerequisites

- Python 3.10+ or Node.js 18+
- A Sardis API key ([Sign up free](https://app.sardis.sh/signup) then create a key at [API Keys](https://app.sardis.sh/api-keys))

## Step 1: Install

=== "Python"

    ```bash
    pip install sardis-sdk
    ```

=== "TypeScript"

    ```bash
    npm install @sardis/sdk
    ```

## Step 2: Create a Wallet

=== "Python"

    ```python
    from sardis import SardisClient

    client = SardisClient(api_key="sk_test_...")

    wallet = client.wallets.create(
        name="my-first-agent",
        chain="base",
        policy="Max $500/day, only OpenAI and AWS"
    )
    print(f"Wallet created: {wallet.id}")
    print(f"Address: {wallet.address}")
    ```

=== "TypeScript"

    ```typescript
    import { SardisClient } from '@sardis/sdk';

    const client = new SardisClient({ apiKey: 'sk_test_...' });

    const wallet = await client.wallets.create({
      name: 'my-first-agent',
      chain: 'base',
      policy: 'Max $500/day, only OpenAI and AWS',
    });
    console.log(`Wallet: ${wallet.id}, Address: ${wallet.address}`);
    ```

## Step 3: Fund the Wallet

For testing, get free testnet USDC on Base Sepolia:

1. **Get testnet ETH** (for gas): [Alchemy Faucet](https://www.alchemy.com/faucets/base-sepolia) or [Coinbase Faucet](https://portal.cdp.coinbase.com/products/faucet)
2. **Get testnet USDC**: [Circle Faucet](https://faucet.circle.com/) — select **Base Sepolia** and **USDC**
3. **Send to your wallet**: Copy your wallet address from Step 2 and paste it in the faucet

!!! tip "Gasless Payments"
    Sardis uses Circle Paymaster for gasless USDC transfers on Base. Your agent doesn't need ETH for gas — USDC covers everything.

For **production**, fund your wallet with real USDC on Base mainnet via any exchange or on-ramp.

## Step 4: Make a Payment

=== "Python"

    ```python
    result = client.payments.execute(
        wallet_id=wallet.id,
        to="0x1234...merchant_address",
        amount=50,
        token="USDC",
        purpose="API credits"
    )
    print(f"TX: {result.tx_hash}")
    print(f"Status: {result.status}")
    ```

=== "TypeScript"

    ```typescript
    const result = await client.payments.execute({
      walletId: wallet.id,
      to: '0x1234...merchant_address',
      amount: 50,
      token: 'USDC',
      purpose: 'API credits',
    });
    console.log(`TX: ${result.txHash}, Status: ${result.status}`);
    ```

## Step 5: Add to Your AI Agent

=== "OpenAI"

    ```python
    pip install sardis-openai
    ```

    ```python
    from sardis_openai import get_sardis_tools, SardisToolHandler

    tools = get_sardis_tools()
    handler = SardisToolHandler(api_key="sk_...")

    response = openai.chat.completions.create(
        model="gpt-4o",
        tools=tools,
        messages=[{"role": "user", "content": "Pay $50 to OpenAI for API credits"}],
    )

    for tool_call in response.choices[0].message.tool_calls:
        result = await handler.handle(tool_call)
    ```

=== "LangChain"

    ```python
    pip install sardis-langchain
    ```

    ```python
    from sardis_langchain import SardisToolkit

    toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
    tools = toolkit.get_tools()
    # Pass to any LangChain agent
    ```

=== "MCP (Claude/Cursor)"

    ```json
    {
      "mcpServers": {
        "sardis": {
          "command": "npx",
          "args": ["@sardis/mcp-server", "start"],
          "env": { "SARDIS_API_KEY": "sk_..." }
        }
      }
    }
    ```

## Next Steps

- [Spending Policies](../concepts/policies.md) - Natural language policy enforcement
- [Integration Guide](../integrations/overview.md) - All supported AI frameworks
- [API Reference](../api/rest.md) - Complete API documentation
