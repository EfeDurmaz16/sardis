# Configuration

## API Key

Get your API key from [sardis.sh](https://sardis.sh) and set it as an environment variable:

```bash
export SARDIS_API_KEY="sk_..."
```

Or pass it directly:

=== "Python"

    ```python
    client = SardisClient(api_key="sk_...")
    ```

=== "TypeScript"

    ```typescript
    const client = new SardisClient({ apiKey: 'sk_...' });
    ```

=== "CLI"

    ```bash
    sardis init  # Interactive setup
    # Or:
    sardis --api-key sk_... wallets list
    ```

## Chains

Sardis supports multiple chains:

| Chain | Network ID | Testnet |
|-------|-----------|---------|
| Base | `base` | `base_sepolia` |
| Polygon | `polygon` | `polygon_amoy` |
| Ethereum | `ethereum` | `ethereum_sepolia` |
| Arbitrum | `arbitrum` | `arbitrum_sepolia` |
| Optimism | `optimism` | `optimism_sepolia` |

## Tokens

| Token | Chains |
|-------|--------|
| USDC | All |
| USDT | Polygon, Ethereum, Arbitrum, Optimism |
| EURC | Base, Polygon, Ethereum |
| PYUSD | Ethereum |

## Simulation Mode

For development and testing, use simulation mode (no real transactions):

```python
from sardis import SardisClient

client = SardisClient(api_key="sk_test_...", simulation=True)
```
