/**
 * Policy Templates Library - Pre-built spending policy templates
 *
 * Provides categorized, one-click policy templates that populate
 * the policy editor with natural language rules.
 */

import { useState } from 'react';
import {
  Cpu,
  ShoppingCart,
  Briefcase,
  BookOpen,
  Users,
  Shield,
  Search,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

// ── Template Data ───────────────────────────────────────────────────────

interface PolicyTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  rules: string;
  tags: string[];
}

const CATEGORIES = [
  { id: 'all', name: 'All Templates', icon: Sparkles },
  { id: 'api', name: 'API Consumption', icon: Cpu },
  { id: 'ecommerce', name: 'E-commerce', icon: ShoppingCart },
  { id: 'procurement', name: 'Procurement', icon: Briefcase },
  { id: 'research', name: 'Research', icon: BookOpen },
  { id: 'multi-agent', name: 'Multi-Agent', icon: Users },
  { id: 'compliance', name: 'Compliance', icon: Shield },
];

const TEMPLATES: PolicyTemplate[] = [
  // API Consumption
  {
    id: 'api-conservative',
    name: 'Conservative API Budget',
    description: 'Strict limits for controlled API spending',
    category: 'api',
    rules: 'Max $50 per day on API calls. Only allow OpenAI, Anthropic, and Google AI. Max $10 per transaction.',
    tags: ['api', 'conservative', 'ai'],
  },
  {
    id: 'api-moderate',
    name: 'Moderate API Budget',
    description: 'Balanced limits for active development',
    category: 'api',
    rules: 'Max $200 per day on API calls. Only allow OpenAI, Anthropic, Google AI, and Cohere. Max $50 per transaction. Require approval above $100.',
    tags: ['api', 'moderate', 'ai'],
  },
  {
    id: 'api-growth',
    name: 'Growth API Budget',
    description: 'Higher limits for production workloads',
    category: 'api',
    rules: 'Max $1000 per day. Max $200 per transaction. Require approval above $500. Block categories: gambling, adult content.',
    tags: ['api', 'growth', 'production'],
  },
  // E-commerce
  {
    id: 'ecom-starter',
    name: 'E-commerce Starter',
    description: 'Basic limits for shopping agents',
    category: 'ecommerce',
    rules: 'Max $100 per order. Max $500 per day. Require approval for orders above $75. Block categories: gambling, adult, cryptocurrency.',
    tags: ['shopping', 'orders', 'approval'],
  },
  {
    id: 'ecom-enterprise',
    name: 'Enterprise Purchasing',
    description: 'Higher limits with multi-approval',
    category: 'ecommerce',
    rules: 'Max $5000 per order. Max $25000 per month. Require approval for orders above $1000. Require 2 approvals above $5000. Only allow approved vendor list.',
    tags: ['enterprise', 'purchasing', 'multi-approval'],
  },
  {
    id: 'ecom-subscription',
    name: 'SaaS Subscription Manager',
    description: 'Manage recurring software subscriptions',
    category: 'ecommerce',
    rules: 'Max $500 per month on subscriptions. Only allow known SaaS providers. Alert on new vendors. Block one-time purchases above $100.',
    tags: ['saas', 'subscriptions', 'recurring'],
  },
  // Procurement
  {
    id: 'proc-standard',
    name: 'Standard Procurement',
    description: 'Vendor-controlled purchasing rules',
    category: 'procurement',
    rules: 'Max $2000 per vendor per month. Only allow approved vendor list. Require approval for new vendors. Require 2 approvals above $5000. Max $10000 per month total.',
    tags: ['procurement', 'vendors', 'approval'],
  },
  {
    id: 'proc-restricted',
    name: 'Restricted Procurement',
    description: 'Tight controls for sensitive purchasing',
    category: 'procurement',
    rules: 'Max $500 per transaction. Max $2000 per week. Only allow pre-approved vendors. Require approval for all transactions. Block international payments.',
    tags: ['restricted', 'sensitive', 'approval'],
  },
  // Research
  {
    id: 'research-academic',
    name: 'Academic Research',
    description: 'Budget for research data and APIs',
    category: 'research',
    rules: 'Max $100 per day total. Only allow academic APIs and data sources. Block commercial marketplaces. Max $500 per month.',
    tags: ['academic', 'research', 'data'],
  },
  {
    id: 'research-lab',
    name: 'Research Lab Budget',
    description: 'Flexible budget for lab experiments',
    category: 'research',
    rules: 'Max $500 per day. Max $5000 per month. Only allow compute and API providers. Require approval above $200. Alert when 80% of monthly budget used.',
    tags: ['lab', 'compute', 'experiments'],
  },
  // Multi-Agent
  {
    id: 'multi-shared',
    name: 'Shared Team Budget',
    description: 'Shared budget across agent fleet',
    category: 'multi-agent',
    rules: 'Shared budget of $5000 per month. Individual agent limit $500 per day. Treasury agent can distribute funds. Other agents cannot transfer to each other.',
    tags: ['team', 'shared', 'treasury'],
  },
  {
    id: 'multi-hierarchy',
    name: 'Hierarchical Spending',
    description: 'Manager-agent approval chains',
    category: 'multi-agent',
    rules: 'Individual limit $100 per transaction. Require manager agent approval above $50. Shared monthly budget $10000. Block cross-agent transfers without approval.',
    tags: ['hierarchy', 'manager', 'approval'],
  },
  {
    id: 'multi-independent',
    name: 'Independent Agent Fleet',
    description: 'Each agent has its own budget',
    category: 'multi-agent',
    rules: 'Each agent gets $1000 per month. Max $200 per transaction per agent. No shared budget. Require human approval above $500.',
    tags: ['independent', 'fleet', 'isolated'],
  },
  // Compliance
  {
    id: 'comp-sanctions',
    name: 'Sanctions Screening',
    description: 'Block sanctioned entities and regions',
    category: 'compliance',
    rules: 'Block sanctioned countries. Require KYC verification for transactions above $3000. Block cryptocurrency-to-cryptocurrency transfers. Log all transactions for audit.',
    tags: ['sanctions', 'kyc', 'audit'],
  },
  {
    id: 'comp-aml',
    name: 'AML Compliance',
    description: 'Anti-money laundering controls',
    category: 'compliance',
    rules: 'Max $10000 per day. Require enhanced due diligence above $5000. Block structuring patterns. Report suspicious activity. Require source of funds documentation above $25000.',
    tags: ['aml', 'due-diligence', 'reporting'],
  },
  {
    id: 'comp-gdpr',
    name: 'Data Protection Compliant',
    description: 'GDPR and data privacy controls',
    category: 'compliance',
    rules: 'Only allow EU-based payment processors. Block data transfers to non-adequate countries. Require explicit consent logging. Max $1000 per transaction without additional verification.',
    tags: ['gdpr', 'privacy', 'eu'],
  },
  {
    id: 'comp-financial',
    name: 'Financial Services Compliance',
    description: 'Controls for regulated financial activities',
    category: 'compliance',
    rules: 'Max $50000 per day. Require dual approval above $10000. Maintain complete audit trail. Block self-dealing transactions. Require segregation of duties for large transfers.',
    tags: ['financial', 'regulated', 'dual-approval'],
  },
];

// ── Component ───────────────────────────────────────────────────────────

interface PolicyTemplatesProps {
  onSelectTemplate: (rules: string) => void;
}

export default function PolicyTemplates({ onSelectTemplate }: PolicyTemplatesProps) {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filtered = TEMPLATES.filter((t) => {
    const matchesCategory = selectedCategory === 'all' || t.category === selectedCategory;
    const matchesSearch = !searchQuery ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.tags.some((tag) => tag.includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#505460' }} />
        <input
          type="text"
          placeholder="Search templates..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg text-sm"
          style={{
            background: '#0A0B0D',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#E0E0E0',
            outline: 'none',
          }}
        />
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const isActive = selectedCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
              style={{
                background: isActive ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${isActive ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.08)'}`,
                color: isActive ? '#818CF8' : '#808080',
              }}
            >
              <Icon size={12} />
              {cat.name}
            </button>
          );
        })}
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filtered.map((template) => (
          <button
            key={template.id}
            onClick={() => onSelectTemplate(template.rules)}
            className="text-left rounded-xl p-4 transition-all group"
            style={{
              background: '#0A0B0D',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)';
              e.currentTarget.style.background = '#0D0E16';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
              e.currentTarget.style.background = '#0A0B0D';
            }}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-white mb-1">{template.name}</h4>
                <p className="text-xs mb-2" style={{ color: '#808080' }}>
                  {template.description}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: '#606070' }}>
                  {template.rules}
                </p>
              </div>
              <ChevronRight
                size={16}
                className="shrink-0 ml-2 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ color: '#818CF8' }}
              />
            </div>
            <div className="flex flex-wrap gap-1 mt-2">
              {template.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(255,255,255,0.04)', color: '#505460' }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-8">
          <p className="text-sm" style={{ color: '#505460' }}>No templates match your search.</p>
        </div>
      )}
    </div>
  );
}
