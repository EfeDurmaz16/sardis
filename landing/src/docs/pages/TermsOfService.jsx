import React from 'react';

const TermsOfService = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
        Terms of Service
      </h1>
      <p className="text-muted-foreground mb-8">Last updated: February 15, 2026</p>

      <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold mb-4">1. Acceptance of Terms</h2>
          <p className="text-muted-foreground leading-relaxed">
            By accessing or using the Sardis platform, API, SDKs, or any related services (collectively, the "Services"),
            you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, you may not
            access or use the Services.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            These Terms constitute a legally binding agreement between you (whether personally or on behalf of an entity)
            and Sardis ("Company," "we," "us," or "our").
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">2. Description of Services</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis provides payment infrastructure for AI agents, including:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Policy-controlled wallets (MPC and smart-account modes)</li>
            <li>Stablecoin payment execution on supported blockchains</li>
            <li>Spending policy management and enforcement</li>
            <li>KYC/AML compliance tools</li>
            <li>APIs, SDKs, and integration tools</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">3. Eligibility</h2>
          <p className="text-muted-foreground leading-relaxed">
            You must be at least 18 years old and have the legal capacity to enter into contracts to use our Services.
            By using the Services, you represent and warrant that you meet these requirements.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Our Services are not available in jurisdictions where cryptocurrency or stablecoin transactions are prohibited.
            You are responsible for ensuring compliance with local laws.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">4. Account Registration</h2>
          <p className="text-muted-foreground leading-relaxed">
            To access certain features, you may need to create an account. You agree to:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Provide accurate and complete registration information</li>
            <li>Maintain the security of your API keys and credentials</li>
            <li>Notify us immediately of any unauthorized access</li>
            <li>Accept responsibility for all activities under your account</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">5. Non-Custodial Services</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis can provide a <strong>non-custodial posture</strong> for stablecoin wallets in live MPC mode.
            This means:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Sardis does not directly hold spendable private keys in that mode</li>
            <li>You retain control of wallet authorization boundaries through provider and policy configuration</li>
            <li>You are solely responsible for securing your wallet credentials</li>
            <li>Lost keys cannot be recovered by Sardis</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Fiat transfers and card settlement are executed by regulated third-party providers and issuers.
            Those rails may involve partner custody and settlement controls outside Sardis-managed key material.
          </p>
          <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 mt-4">
            <p className="text-yellow-600 dark:text-yellow-400 font-medium">
              Warning: Cryptocurrency transactions are irreversible. Once a transaction is confirmed on the
              blockchain, it cannot be undone. Always verify transaction details before confirmation.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">6. Compliance and KYC/AML</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis implements Know Your Customer (KYC) and Anti-Money Laundering (AML) procedures. You agree to:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Provide accurate identity verification information when requested</li>
            <li>Not use the Services for money laundering, terrorist financing, or other illegal activities</li>
            <li>Comply with all applicable sanctions and export control laws</li>
            <li>Allow us to screen transactions against sanctions lists</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">7. Prohibited Uses</h2>
          <p className="text-muted-foreground leading-relaxed">You may not use the Services to:</p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Violate any applicable laws or regulations</li>
            <li>Process payments for illegal goods or services</li>
            <li>Engage in fraud, money laundering, or terrorist financing</li>
            <li>Circumvent spending policies or compliance controls</li>
            <li>Interfere with or disrupt the Services</li>
            <li>Attempt to gain unauthorized access to our systems</li>
            <li>Reverse engineer or decompile our software (except as permitted by law)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">8. Fees and Payment</h2>
          <p className="text-muted-foreground leading-relaxed">
            Certain Services may be subject to fees. Current pricing is available at sardis.sh/pricing.
            We reserve the right to change our fees with 30 days notice.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Blockchain transaction fees (gas fees) are separate from Sardis fees. Depending on wallet type and
            route, gas may be paid directly by your wallet or sponsored by a configured paymaster.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">9. Intellectual Property</h2>
          <p className="text-muted-foreground leading-relaxed">
            The Services, including all software, documentation, and content, are protected by intellectual
            property laws. We grant you a limited, non-exclusive, non-transferable license to use the Services
            in accordance with these Terms.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Our open-source components are governed by their respective licenses (e.g., MIT, Apache 2.0).
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">10. Disclaimer of Warranties</h2>
          <p className="text-muted-foreground leading-relaxed">
            THE SERVICES ARE PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
            EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY,
            FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            We do not warrant that the Services will be uninterrupted, secure, or error-free.
            Cryptocurrency markets are volatile, and we make no guarantees regarding asset values.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">11. Limitation of Liability</h2>
          <p className="text-muted-foreground leading-relaxed">
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, SARDIS SHALL NOT BE LIABLE FOR ANY INDIRECT,
            INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO
            LOSS OF PROFITS, DATA, OR DIGITAL ASSETS, REGARDLESS OF THE CAUSE OF ACTION OR THE
            THEORY OF LIABILITY.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Our total liability shall not exceed the fees paid by you to Sardis in the twelve (12)
            months preceding the claim.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">12. Indemnification</h2>
          <p className="text-muted-foreground leading-relaxed">
            You agree to indemnify and hold harmless Sardis, its affiliates, and their respective officers,
            directors, employees, and agents from any claims, damages, losses, or expenses arising from:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Your use of the Services</li>
            <li>Your violation of these Terms</li>
            <li>Your violation of any third-party rights</li>
            <li>Your AI agents' actions or transactions</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">13. Termination</h2>
          <p className="text-muted-foreground leading-relaxed">
            We may suspend or terminate your access to the Services at any time for violation of these Terms
            or for any reason with notice. You may terminate your account at any time by contacting support.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Upon termination, you retain control of your non-custodial wallets, but you will lose access
            to Sardis-specific features and policies.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">14. Governing Law</h2>
          <p className="text-muted-foreground leading-relaxed">
            These Terms shall be governed by and construed in accordance with the laws of Delaware, USA,
            without regard to its conflict of law provisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">15. Dispute Resolution</h2>
          <p className="text-muted-foreground leading-relaxed">
            Any disputes arising from these Terms or the Services shall first be resolved through good-faith
            negotiation. If negotiation fails, disputes shall be resolved through binding arbitration in
            accordance with the rules of the American Arbitration Association.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">16. Changes to Terms</h2>
          <p className="text-muted-foreground leading-relaxed">
            We may update these Terms from time to time. We will notify you of material changes by posting
            the updated Terms on our website with a new "Last updated" date. Your continued use of the
            Services after such changes constitutes acceptance of the updated Terms.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">17. Contact Information</h2>
          <p className="text-muted-foreground leading-relaxed">
            If you have any questions about these Terms, please contact us at:
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

export default TermsOfService;
