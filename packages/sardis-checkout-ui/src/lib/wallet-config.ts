import { http, createConfig } from "wagmi";
import { base, baseSepolia } from "wagmi/chains";
import { coinbaseWallet, walletConnect } from "wagmi/connectors";

const isTestnet = import.meta.env.VITE_CHAIN === "base_sepolia";
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || "";

const connectors = [
  coinbaseWallet({
    appName: "Sardis Checkout",
    preference: { options: "all" as const },
  }),
  ...(projectId
    ? [walletConnect({ projectId, showQrModal: true })]
    : []),
];

export const wagmiConfig = isTestnet
  ? createConfig({
      chains: [baseSepolia],
      connectors,
      transports: { [baseSepolia.id]: http() },
    })
  : createConfig({
      chains: [base],
      connectors,
      transports: { [base.id]: http() },
    });

export const USDC_ADDRESS = isTestnet
  ? "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
  : "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";

export const USDC_DECIMALS = 6;
