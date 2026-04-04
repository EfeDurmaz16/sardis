# sardis-e2b

E2B sandbox template for running Sardis-enabled AI agents in isolated, ephemeral environments.

## Overview

This package provides an E2B sandbox template with the Sardis SDK pre-installed and configured for simulation mode. It lets you test agent payment flows safely before going live.

## Quick Start

### 1. Build and Push the Template

```bash
# Install E2B CLI
npm install -g @e2b/cli

# Authenticate
e2b auth login

# Build and deploy the template from this directory
e2b template build --name sardis-agent
```

This produces a template ID (e.g., `sardis-agent-abc123`).

### 2. Use the Template in Your Agent

```python
from e2b import Sandbox

with Sandbox(template="sardis-agent") as sandbox:
    # Upload your agent code
    sandbox.filesystem.write("/home/user/agent.py", open("my_agent.py").read())

    # Run it
    proc = sandbox.process.start("python /home/user/agent.py")
    proc.wait()
    print(proc.stdout)
```

### 3. Pass Real API Keys (Optional)

For production-mode payments (not simulation), pass your Sardis API key as an environment variable:

```python
with Sandbox(
    template="sardis-agent",
    env_vars={"SARDIS_API_KEY": "sk_live_...", "SARDIS_SIMULATION": "false"},
) as sandbox:
    ...
```

## Simulation Mode

By default, `SARDIS_SIMULATION=true` is set in the Dockerfile. In simulation mode:

- No real transactions are submitted on-chain
- Wallet and balance data is mocked
- Useful for CI pipelines, integration tests, and agent prototyping

Set `SARDIS_SIMULATION=false` to execute real transactions.

## Example

See `examples/sandbox_agent.py` for a minimal working example that creates a wallet and executes a simulated payment inside the sandbox.

## Template Contents

| File | Purpose |
|------|---------|
| `e2b.Dockerfile` | Sandbox image — Python + Sardis SDK pre-installed |
| `examples/sandbox_agent.py` | Minimal payment agent example |

## Links

- [E2B Documentation](https://e2b.dev/docs)
- [Sardis Documentation](https://sardis.sh/docs)
- [Sardis Python SDK](https://pypi.org/project/sardis)
