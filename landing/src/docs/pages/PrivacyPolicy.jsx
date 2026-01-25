import React from 'react';

const PrivacyPolicy = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
        Privacy Policy
      </h1>
      <p className="text-muted-foreground mb-8">Last updated: January 25, 2026</p>

      <div className="prose prose-slate dark:prose-invert max-w-none space-y-8">
        <section>
          <h2 className="text-xl font-semibold mb-4">1. Introduction</h2>
          <p className="text-muted-foreground leading-relaxed">
            Sardis ("Company," "we," "us," or "our") respects your privacy and is committed to protecting
            your personal data. This Privacy Policy explains how we collect, use, disclose, and safeguard
            your information when you use our platform, APIs, and services.
          </p>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Please read this Privacy Policy carefully. By using our Services, you consent to the practices
            described in this policy.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">2. Information We Collect</h2>

          <h3 className="text-lg font-medium mt-6 mb-3">2.1 Information You Provide</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li><strong>Account Information:</strong> Name, email address, organization name</li>
            <li><strong>Identity Verification:</strong> Government ID, address, date of birth (for KYC)</li>
            <li><strong>Payment Information:</strong> Billing address, payment method details</li>
            <li><strong>Communications:</strong> Messages you send to our support team</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">2.2 Information Collected Automatically</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li><strong>Usage Data:</strong> API calls, feature usage, error logs</li>
            <li><strong>Device Information:</strong> IP address, browser type, operating system</li>
            <li><strong>Blockchain Data:</strong> Wallet addresses, transaction hashes (public data)</li>
            <li><strong>Cookies:</strong> Session cookies, analytics cookies (see Cookie section)</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">2.3 Information from Third Parties</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li><strong>Identity Verification:</strong> Data from Persona (KYC provider)</li>
            <li><strong>Sanctions Screening:</strong> Results from Elliptic (AML provider)</li>
            <li><strong>Blockchain Data:</strong> Public transaction data from blockchain networks</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">3. How We Use Your Information</h2>
          <p className="text-muted-foreground leading-relaxed">We use collected information to:</p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Provide and maintain our Services</li>
            <li>Process transactions and manage your account</li>
            <li>Comply with KYC/AML and other legal requirements</li>
            <li>Prevent fraud and enforce spending policies</li>
            <li>Send service-related communications</li>
            <li>Improve and personalize our Services</li>
            <li>Respond to your requests and support inquiries</li>
            <li>Analyze usage patterns and optimize performance</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">4. Legal Basis for Processing (GDPR)</h2>
          <p className="text-muted-foreground leading-relaxed">
            For users in the European Economic Area (EEA), we process personal data based on:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Contract Performance:</strong> To provide Services you requested</li>
            <li><strong>Legal Obligations:</strong> To comply with KYC/AML requirements</li>
            <li><strong>Legitimate Interests:</strong> To improve Services and prevent fraud</li>
            <li><strong>Consent:</strong> For marketing communications (where required)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">5. Information Sharing</h2>
          <p className="text-muted-foreground leading-relaxed">We may share your information with:</p>

          <h3 className="text-lg font-medium mt-6 mb-3">5.1 Service Providers</h3>
          <ul className="list-disc list-inside text-muted-foreground space-y-2">
            <li><strong>Turnkey:</strong> MPC wallet infrastructure (non-custodial)</li>
            <li><strong>Persona:</strong> Identity verification (KYC)</li>
            <li><strong>Elliptic:</strong> Sanctions and AML screening</li>
            <li><strong>Cloud Providers:</strong> AWS, GCP for infrastructure</li>
          </ul>

          <h3 className="text-lg font-medium mt-6 mb-3">5.2 Legal Requirements</h3>
          <p className="text-muted-foreground leading-relaxed">
            We may disclose information when required by law, court order, or government request,
            or to protect our rights, safety, or property.
          </p>

          <h3 className="text-lg font-medium mt-6 mb-3">5.3 Business Transfers</h3>
          <p className="text-muted-foreground leading-relaxed">
            In the event of a merger, acquisition, or sale of assets, your information may be
            transferred to the acquiring entity.
          </p>

          <div className="bg-emerald-500/10 border border-emerald-500/30 p-4 mt-4">
            <p className="text-emerald-600 dark:text-emerald-400">
              <strong>We Never Sell Your Data:</strong> We do not sell, rent, or trade your personal
              information to third parties for marketing purposes.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">6. Data Retention</h2>
          <p className="text-muted-foreground leading-relaxed">We retain your data for:</p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Account Data:</strong> Duration of account + 3 years</li>
            <li><strong>Transaction Records:</strong> 7 years (regulatory requirement)</li>
            <li><strong>KYC Documents:</strong> 5-7 years depending on jurisdiction</li>
            <li><strong>Audit Logs:</strong> 7 years (compliance requirement)</li>
            <li><strong>Usage Analytics:</strong> 2 years (anonymized after)</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">7. Your Rights</h2>
          <p className="text-muted-foreground leading-relaxed">Depending on your location, you may have the right to:</p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Access:</strong> Request a copy of your personal data</li>
            <li><strong>Rectification:</strong> Correct inaccurate or incomplete data</li>
            <li><strong>Erasure:</strong> Request deletion of your data (with limitations)</li>
            <li><strong>Portability:</strong> Receive your data in a portable format</li>
            <li><strong>Objection:</strong> Object to certain processing activities</li>
            <li><strong>Restriction:</strong> Request limited processing of your data</li>
            <li><strong>Withdraw Consent:</strong> Where processing is based on consent</li>
          </ul>

          <div className="bg-yellow-500/10 border border-yellow-500/30 p-4 mt-4">
            <p className="text-yellow-600 dark:text-yellow-400">
              <strong>Note:</strong> Some data (e.g., transaction records, audit logs) cannot be deleted
              due to regulatory requirements. Blockchain data is permanent and immutable.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">8. Data Security</h2>
          <p className="text-muted-foreground leading-relaxed">
            We implement industry-standard security measures including:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Encryption in transit (TLS 1.3) and at rest (AES-256)</li>
            <li>Non-custodial architecture (we never hold your private keys)</li>
            <li>MPC technology for secure transaction signing</li>
            <li>Regular security audits and penetration testing</li>
            <li>SOC 2 Type II compliance (in progress)</li>
            <li>Access controls and audit logging</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            Despite our efforts, no system is completely secure. We cannot guarantee absolute security
            of your data.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">9. Cookies and Tracking</h2>
          <p className="text-muted-foreground leading-relaxed">We use the following types of cookies:</p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li><strong>Essential Cookies:</strong> Required for site functionality</li>
            <li><strong>Analytics Cookies:</strong> To understand how you use our Services</li>
            <li><strong>Preference Cookies:</strong> To remember your settings</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed mt-3">
            You can control cookies through your browser settings. Disabling cookies may affect
            functionality.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">10. International Transfers</h2>
          <p className="text-muted-foreground leading-relaxed">
            Your data may be transferred to and processed in countries outside your jurisdiction,
            including the United States. We ensure appropriate safeguards are in place, such as
            Standard Contractual Clauses (SCCs) for EEA data.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">11. Children's Privacy</h2>
          <p className="text-muted-foreground leading-relaxed">
            Our Services are not intended for individuals under 18 years of age. We do not knowingly
            collect personal information from children. If we learn we have collected data from a child,
            we will delete it promptly.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">12. California Privacy Rights (CCPA)</h2>
          <p className="text-muted-foreground leading-relaxed">
            California residents have additional rights under the CCPA, including:
          </p>
          <ul className="list-disc list-inside text-muted-foreground mt-3 space-y-2">
            <li>Right to know what personal information we collect</li>
            <li>Right to delete personal information</li>
            <li>Right to opt-out of sale (we do not sell data)</li>
            <li>Right to non-discrimination for exercising rights</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">13. Changes to This Policy</h2>
          <p className="text-muted-foreground leading-relaxed">
            We may update this Privacy Policy from time to time. We will notify you of material changes
            by updating the "Last updated" date and, for significant changes, by email or prominent
            notice on our website.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-4">14. Contact Us</h2>
          <p className="text-muted-foreground leading-relaxed">
            If you have questions about this Privacy Policy or wish to exercise your rights, contact us:
          </p>
          <div className="bg-card border border-border p-4 mt-4 font-mono text-sm">
            <p>Email: privacy@sardis.sh</p>
            <p>Data Protection Officer: dpo@sardis.sh</p>
            <p>Website: https://sardis.sh</p>
          </div>
          <p className="text-muted-foreground leading-relaxed mt-4">
            For EEA residents, you have the right to lodge a complaint with your local data protection
            authority if you believe we have violated your privacy rights.
          </p>
        </section>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
