import React from 'react';

const AcceptableUse = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
        Acceptable Use Policy
      </h1>
      <p className="text-muted-foreground mb-8">Last updated: January 27, 2026</p>

      <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold mb-4">1. Overview</h2>
          <p className="text-muted-foreground leading-relaxed">
            This Acceptable Use Policy ("AUP") governs your use of Sardis payment infrastructure for AI agents.
            By using our Services, you agree to comply with this AUP. Violation of this policy may result in
            immediate suspension or termination of your account.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">2. Permitted Uses</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis is designed for legitimate AI agent payment operations, including:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>AI agents paying for API services (OpenAI, Anthropic, etc.)</li>
            <li>Automated procurement of digital goods and services</li>
            <li>Agent-to-agent transactions for collaborative tasks</li>
            <li>Subscription and billing management for AI workflows</li>
            <li>Development, testing, and integration of payment features</li>
            <li>Research and educational purposes in AI economics</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">3. Prohibited Activities</h2>
          <p className="text-muted-foreground leading-relaxed">
            You may NOT use Sardis for any of the following activities:
          </p>

          <h3 className="text-lg font-medium mt-6 mb-3">3.1 Illegal Activities</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Money laundering or terrorist financing</li>
            <li>Sanctions evasion or trade with restricted countries/entities</li>
            <li>Tax evasion or fraudulent financial reporting</li>
            <li>Payments for illegal drugs, weapons, or controlled substances</li>
            <li>Human trafficking or exploitation</li>
            <li>Child sexual abuse material (CSAM) or child exploitation</li>
            <li>Any activity that violates applicable laws or regulations</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">3.2 Fraud and Deception</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Identity fraud or impersonation</li>
            <li>Phishing, scams, or social engineering</li>
            <li>Unauthorized access to others' wallets or accounts</li>
            <li>Market manipulation or pump-and-dump schemes</li>
            <li>Fake or misleading merchant descriptions</li>
            <li>Circumventing spending policies or compliance controls</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">3.3 Harmful Content and Services</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Payment for malware, ransomware, or hacking tools</li>
            <li>DDoS attacks or other cyberattacks</li>
            <li>Disinformation campaigns or election interference</li>
            <li>Harassment, stalking, or doxxing services</li>
            <li>Non-consensual intimate imagery</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">3.4 Restricted Financial Activities</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Unlicensed money transmission or remittance</li>
            <li>Operating as an unlicensed exchange or broker</li>
            <li>Pyramid schemes or Ponzi schemes</li>
            <li>Unlicensed securities offerings</li>
            <li>Gambling (unless properly licensed and geo-restricted)</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">3.5 System Abuse</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li>Attempting to bypass rate limits or abuse APIs</li>
            <li>Reverse engineering, decompiling, or exploiting vulnerabilities</li>
            <li>Interfering with other users' access to the Services</li>
            <li>Using the Services for stress testing without permission</li>
            <li>Automated account creation to circumvent limits</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">4. High-Risk Categories</h2>
          <p className="text-muted-foreground leading-relaxed">
            The following categories require enhanced due diligence and may be subject to additional restrictions:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Adult Content:</strong> Must comply with all applicable laws, age verification required</li>
            <li><strong>Gambling:</strong> Must be licensed, geo-restricted to permitted jurisdictions</li>
            <li><strong>Cryptocurrency Services:</strong> Must comply with local regulations</li>
            <li><strong>Firearms and Ammunition:</strong> Must comply with all applicable laws</li>
            <li><strong>Pharmaceuticals:</strong> Must be properly licensed</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Contact legal@sardis.sh before enabling transactions in these categories.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">5. AI Agent Responsibilities</h2>
          <p className="text-muted-foreground leading-relaxed">
            When using Sardis with AI agents, you are responsible for:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Policy Configuration:</strong> Setting appropriate spending limits and category restrictions</li>
            <li><strong>Monitoring:</strong> Reviewing agent transactions for anomalies</li>
            <li><strong>Human Oversight:</strong> Maintaining ability to pause or revoke agent permissions</li>
            <li><strong>Prompt Safety:</strong> Ensuring agent prompts don't encourage policy violations</li>
            <li><strong>Logging:</strong> Maintaining audit trails for agent decision-making</li>
          </ul>

          <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 mt-4">
            <p className="text-yellow-600 dark:text-yellow-400">
              <strong>Important:</strong> You are legally responsible for all transactions executed by your
              AI agents. "The AI did it" is not a valid defense for policy violations or illegal activity.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">6. Compliance Requirements</h2>
          <p className="text-muted-foreground leading-relaxed">All users must:</p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Complete identity verification (KYC) when required</li>
            <li>Provide accurate information about the nature of transactions</li>
            <li>Cooperate with compliance investigations</li>
            <li>Maintain appropriate records for tax and regulatory purposes</li>
            <li>Not knowingly transact with sanctioned parties</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">7. Reporting Violations</h2>
          <p className="text-muted-foreground leading-relaxed">
            If you become aware of any violations of this AUP, please report them to:
          </p>
          <div className="bg-card border border-border p-4 mt-4 font-mono text-sm">
            <p>Email: contact@sardis.sh</p>
            <p>Security Issues: dev@sardis.sh</p>
          </div>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Reports are confidential. We do not retaliate against good-faith reporters.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">8. Enforcement</h2>
          <p className="text-muted-foreground leading-relaxed">
            Violations of this AUP may result in:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Warning:</strong> For minor, first-time violations</li>
            <li><strong>Temporary Suspension:</strong> Pending investigation</li>
            <li><strong>Permanent Termination:</strong> For serious or repeated violations</li>
            <li><strong>Fund Freezing:</strong> Where required by law or court order</li>
            <li><strong>Legal Action:</strong> We may report illegal activities to authorities</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            We reserve the right to take any action we deem appropriate to enforce this policy.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">9. Appeals</h2>
          <p className="text-muted-foreground leading-relaxed">
            If you believe your account was suspended in error, you may appeal by contacting
            legal@sardis.sh with:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Your account identifier</li>
            <li>Description of the situation</li>
            <li>Any evidence supporting your case</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Appeals are reviewed within 10 business days. Decisions are final.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">10. Changes to This Policy</h2>
          <p className="text-muted-foreground leading-relaxed">
            We may update this AUP to reflect changes in our Services or legal requirements.
            Material changes will be communicated via email or prominent notice. Continued use
            of the Services constitutes acceptance of the updated policy.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">11. Contact</h2>
          <p className="text-muted-foreground leading-relaxed">
            For questions about this Acceptable Use Policy:
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

export default AcceptableUse;
