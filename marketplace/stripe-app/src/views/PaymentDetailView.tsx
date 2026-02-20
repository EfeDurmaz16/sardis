import {
  Box,
  ContextView,
  Badge,
  List,
  ListItem,
  Divider,
  Banner,
} from '@stripe/ui-extension-sdk/ui';
import type { ExtensionContextValue } from '@stripe/ui-extension-sdk/context';

/**
 * Sardis Payment Detail View
 *
 * Shows Sardis-specific details for a Stripe payment:
 * - Which agent made the payment
 * - Policy that authorized it
 * - KYA verification status
 * - Ledger entry reference
 */
const PaymentDetailView = ({
  environment,
}: ExtensionContextValue) => {
  return (
    <ContextView
      title="Sardis Agent Details"
      description="AI agent payment context"
    >
      <Box css={{ marginBottom: 'medium' }}>
        <Banner
          type="positive"
          title="Policy Authorized"
          description="This payment was authorized by Sardis spending policy."
        />
      </Box>

      <List>
        <ListItem
          title="Agent"
          value="procurement-agent"
        />
        <ListItem
          title="Agent Owner"
          value="Acme Corp (KYA Verified)"
        />
        <ListItem
          title="Policy"
          value="Max $500/day, SaaS only"
        />
        <ListItem
          title="KYA Level"
          value={<Badge type="positive">Level 2 - Verified</Badge>}
        />
        <ListItem
          title="Authorization"
          value="< 200ms"
        />
      </List>

      <Divider />

      <Box css={{ font: 'heading', marginBottom: 'small', marginTop: 'medium' }}>
        Audit Trail
      </Box>

      <List>
        <ListItem
          title="Ledger Entry"
          value="LE-2026-04821"
        />
        <ListItem
          title="Mandate ID"
          value="mnd_a1b2c3d4..."
        />
        <ListItem
          title="Audit Hash"
          value="sha256:e3b0c44..."
        />
        <ListItem
          title="Wallet"
          value="0x742d...5f2b (Base)"
        />
      </List>
    </ContextView>
  );
};

export default PaymentDetailView;
