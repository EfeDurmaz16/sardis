import React from 'react';

const RiskDisclosures = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
        Risk Disclosures
      </h1>
      <p className="text-muted-foreground mb-8">Last updated: January 27, 2026</p>

      <div className="bg-red-500/10 border border-red-500/30 p-6 mb-8">
        <p className="text-red-600 dark:text-red-400 font-semibold text-lg mb-2">
          Important: Please Read Carefully
        </p>
        <p className="text-red-600 dark:text-red-400">
          Using Sardis and digital asset payments involves significant risks. You could lose some or all
          of your funds. Only use funds you can afford to lose. This document does not constitute
          financial, legal, or investment advice.
        </p>
      </div>

      <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold mb-4">1. Overview</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis provides payment infrastructure for AI agents using blockchain technology and stablecoins.
            While we implement security measures and compliance controls, there are inherent risks you should
            understand before using our Services.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">2. Cryptocurrency and Stablecoin Risks</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">2.1 Price Volatility</h3>
          <p className="text-muted-foreground leading-relaxed">
            While stablecoins are designed to maintain a stable value, they may:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Deviate from their peg temporarily or permanently (e.g., UST collapse in 2022)</li>
            <li>Experience liquidity issues during market stress</li>
            <li>Be affected by the issuer's financial health or reserve management</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">2.2 Stablecoin-Specific Risks</h3>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>USDC:</strong> Centralized, can be frozen by Circle; backed by USD reserves</li>
            <li><strong>USDT:</strong> Questions about reserve transparency; can be frozen by Tether</li>
            <li><strong>DAI:</strong> Algorithmic; exposed to underlying collateral volatility</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            We primarily support USDC for its regulatory compliance and transparent reserves, but
            no stablecoin is risk-free.
          </p>

          <h3 className="text-lg font-medium mt-6 mb-3">2.3 Regulatory Risk</h3>
          <p className="text-muted-foreground leading-relaxed">
            Cryptocurrency regulations are evolving. Future laws may:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Restrict or ban stablecoin transactions in certain jurisdictions</li>
            <li>Require additional licensing or compliance measures</li>
            <li>Affect the availability of certain features or services</li>
            <li>Impact the value or usability of digital assets</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">3. Blockchain and Technology Risks</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">3.1 Transaction Irreversibility</h3>
          <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 mt-2 mb-4">
            <p className="text-yellow-600 dark:text-yellow-400">
              <strong>Critical:</strong> Blockchain transactions cannot be reversed. Sending funds to the
              wrong address, making errors in transaction amounts, or falling victim to fraud may result
              in permanent loss of funds with no recourse.
            </p>
          </div>

          <h3 className="text-lg font-medium mt-6 mb-3">3.2 Smart Contract Risks</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Smart contracts may contain bugs or vulnerabilities</li>
            <li>Exploits could result in loss of funds</li>
            <li>Contract upgrades may change behavior unexpectedly</li>
            <li>Dependency on external protocols (bridges, DEXs) introduces additional risk</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">3.3 Network Risks</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li><strong>Congestion:</strong> High network activity may cause delays or high fees</li>
            <li><strong>Downtime:</strong> Networks may experience outages or degraded performance</li>
            <li><strong>Forks:</strong> Chain splits may cause confusion or temporary inaccessibility</li>
            <li><strong>51% Attacks:</strong> Theoretical risk of consensus manipulation</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">3.4 MEV (Miner Extractable Value)</h3>
          <p className="text-muted-foreground leading-relaxed">
            Transactions on public blockchains may be subject to front-running, sandwich attacks,
            or other MEV extraction. While we implement MEV protection measures, complete protection
            is not guaranteed.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">4. Custody and Security Risks</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">4.1 Non-Custodial Architecture</h3>
          <p className="text-muted-foreground leading-relaxed">
            Sardis uses non-custodial MPC (Multi-Party Computation) wallets:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Benefit:</strong> You maintain control of your assets; we cannot access them</li>
            <li><strong>Risk:</strong> If you lose access to your credentials, funds cannot be recovered</li>
            <li><strong>MPC Risk:</strong> While MPC eliminates single points of failure, coordinated
              compromise of key shares could still occur</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">4.2 Security Risks</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>API keys may be compromised if not properly secured</li>
            <li>Phishing attacks may trick you into revealing credentials</li>
            <li>Third-party service providers (Turnkey, etc.) may experience breaches</li>
            <li>Zero-day vulnerabilities may affect any software system</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">4.3 No FDIC Insurance</h3>
          <div className="bg-red-500/10 border border-red-500/30 p-4 mt-2">
            <p className="text-red-600 dark:text-red-400">
              Digital assets held in Sardis wallets are <strong>NOT</strong> insured by the FDIC,
              SIPC, or any government agency. Unlike bank deposits, there is no guarantee of recovery
              if assets are lost due to hacks, insolvency, or other causes.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">5. AI Agent Risks</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">5.1 Autonomous Decision-Making</h3>
          <p className="text-muted-foreground leading-relaxed">
            AI agents using Sardis may make financial decisions autonomously. Risks include:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Hallucinations:</strong> AI may misinterpret data or make unfounded decisions</li>
            <li><strong>Prompt Injection:</strong> Malicious inputs may manipulate agent behavior</li>
            <li><strong>Unintended Actions:</strong> Agents may execute transactions you didn't intend</li>
            <li><strong>Runaway Spending:</strong> Improperly configured limits may allow excessive spending</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">5.2 Policy Limitations</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Spending policies may not cover all edge cases</li>
            <li>Natural language policies require interpretation which may be imperfect</li>
            <li>Time-based limits reset, potentially allowing accumulated overspending</li>
            <li>Category detection depends on merchant data accuracy</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">5.3 Your Responsibility</h3>
          <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 mt-2">
            <p className="text-yellow-600 dark:text-yellow-400">
              <strong>You are legally responsible for all actions taken by your AI agents.</strong>
              Always implement appropriate spending limits, monitor agent activity, and maintain
              the ability to pause or revoke agent permissions immediately.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">6. Operational Risks</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">6.1 Service Availability</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>The Services may experience downtime for maintenance or due to technical issues</li>
            <li>Third-party dependencies (RPC providers, etc.) may affect availability</li>
            <li>DDoS attacks or other malicious activity may disrupt service</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">6.2 Third-Party Risks</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li><strong>Turnkey:</strong> MPC wallet infrastructure provider</li>
            <li><strong>Persona:</strong> Identity verification (KYC)</li>
            <li><strong>Elliptic:</strong> Sanctions and AML screening</li>
            <li><strong>Bridge:</strong> Fiat on/off ramp provider</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Issues with any of these providers could affect your ability to use the Services.
          </p>

          <h3 className="text-lg font-medium mt-6 mb-3">6.3 Company Risk</h3>
          <p className="text-muted-foreground leading-relaxed">
            Sardis is an early-stage company. Risks include:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>The company may cease operations</li>
            <li>Services may be discontinued or significantly changed</li>
            <li>Business model may change, affecting pricing or features</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Because wallets are non-custodial, you would retain access to your funds even if
            Sardis ceases operations (though Sardis-specific features would be unavailable).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">7. Regulatory and Legal Risks</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">7.1 Money Transmission</h3>
          <p className="text-muted-foreground leading-relaxed">
            Sardis operates as a technology provider, not a money transmitter. Our non-custodial
            architecture means we do not hold or transmit customer funds. However:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Regulatory interpretations may change</li>
            <li>Some jurisdictions may apply different standards</li>
            <li>Future regulations may require licensing</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">7.2 Tax Implications</h3>
          <p className="text-muted-foreground leading-relaxed">
            Cryptocurrency transactions may have tax implications. You are responsible for:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Reporting transactions to tax authorities as required</li>
            <li>Maintaining records for tax purposes</li>
            <li>Consulting with tax professionals about your specific situation</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">7.3 Compliance Risks</h3>
          <p className="text-muted-foreground leading-relaxed">
            If you use Sardis for business purposes, you may have regulatory obligations:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>KYC/AML requirements for your own customers</li>
            <li>Financial services licensing depending on your jurisdiction</li>
            <li>Data protection and privacy requirements</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">8. Risk Mitigation Recommendations</h2>
          <p className="text-muted-foreground leading-relaxed">
            To reduce your risk exposure:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Start Small:</strong> Begin with small amounts until you're comfortable</li>
            <li><strong>Set Conservative Limits:</strong> Configure strict spending policies</li>
            <li><strong>Monitor Activity:</strong> Regularly review transactions and agent behavior</li>
            <li><strong>Secure Credentials:</strong> Use strong passwords, 2FA, and secure key storage</li>
            <li><strong>Diversify:</strong> Don't keep all funds in a single wallet or service</li>
            <li><strong>Stay Informed:</strong> Follow blockchain security news and updates</li>
            <li><strong>Test Thoroughly:</strong> Use testnet before mainnet deployments</li>
            <li><strong>Have a Plan:</strong> Know how to pause agents and secure funds if needed</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">9. No Guarantees</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis makes no guarantees about:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>The value or stability of any digital assets</li>
            <li>The security or availability of the Services</li>
            <li>The accuracy of AI agent decisions or policy evaluations</li>
            <li>Protection against all possible losses or attacks</li>
            <li>Future regulatory treatment of digital assets</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">10. Acknowledgment</h2>
          <p className="text-muted-foreground leading-relaxed">
            By using Sardis, you acknowledge that:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>You have read and understood these risk disclosures</li>
            <li>You accept the risks associated with using the Services</li>
            <li>You are using funds you can afford to lose</li>
            <li>You will not hold Sardis liable for losses resulting from these risks</li>
            <li>You have consulted with professional advisors as appropriate</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">11. Contact</h2>
          <p className="text-muted-foreground leading-relaxed">
            For questions about these risk disclosures:
          </p>
          <div className="bg-card border border-border p-4 mt-4 font-mono text-sm">
            <p>Email: legal@sardis.sh</p>
            <p>Website: https://sardis.sh</p>
          </div>
        </section>
      </div>
    </div>
  );
};

export default RiskDisclosures;
