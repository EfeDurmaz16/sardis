import {
  Box,
  ContextView,
  Inline,
  Badge,
  List,
  ListItem,
  Link,
  Banner,
  Divider,
} from '@stripe/ui-extension-sdk/ui';
import type { ExtensionContextValue } from '@stripe/ui-extension-sdk/context';

/**
 * Sardis Agent Overview - Stripe Dashboard Home View
 *
 * Shows AI agent spending summary, active cards, and policy status.
 */
const AgentOverviewView = ({ environment }: ExtensionContextValue) => {
  return (
    <ContextView
      title="Sardis Agent Payments"
      description="AI agent spending overview"
      actions={[
        {
          label: 'Open Dashboard',
          href: 'https://sardis.sh/dashboard',
        },
      ]}
    >
      <Box css={{ marginBottom: 'medium' }}>
        <Banner
          type="default"
          title="Payment OS for the Agent Economy"
          description="Manage AI agent wallets, spending policies, and virtual cards."
        />
      </Box>

      <Box css={{ font: 'heading', marginBottom: 'small' }}>
        Active Agents
      </Box>

      <List>
        <ListItem
          title="procurement-agent"
          secondaryTitle="$1,200 / $2,000 monthly limit"
          value={<Badge type="positive">Active</Badge>}
        />
        <ListItem
          title="api-buyer-agent"
          secondaryTitle="$450 / $500 monthly limit"
          value={<Badge type="warning">Near limit</Badge>}
        />
        <ListItem
          title="research-agent"
          secondaryTitle="$50 / $1,000 monthly limit"
          value={<Badge type="positive">Active</Badge>}
        />
      </List>

      <Divider />

      <Box css={{ font: 'heading', marginBottom: 'small', marginTop: 'medium' }}>
        Quick Stats
      </Box>

      <Inline css={{ gap: 'large' }}>
        <Box>
          <Box css={{ font: 'caption', color: 'secondary' }}>Total Spent (Month)</Box>
          <Box css={{ font: 'heading' }}>$1,700.00</Box>
        </Box>
        <Box>
          <Box css={{ font: 'caption', color: 'secondary' }}>Active Cards</Box>
          <Box css={{ font: 'heading' }}>3</Box>
        </Box>
        <Box>
          <Box css={{ font: 'caption', color: 'secondary' }}>Policy Blocks</Box>
          <Box css={{ font: 'heading' }}>2</Box>
        </Box>
      </Inline>

      <Divider />

      <Box css={{ marginTop: 'medium' }}>
        <Link href="https://sardis.sh/docs" external>
          Documentation
        </Link>
        {' | '}
        <Link href="https://sardis.sh/dashboard" external>
          Full Dashboard
        </Link>
      </Box>
    </ContextView>
  );
};

export default AgentOverviewView;
