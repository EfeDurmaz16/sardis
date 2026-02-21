import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { colors } from '../theme/colors';
import { sardisApi } from '../api/sardisApi';
import { Agent, QuickStats } from '../types';

const { width } = Dimensions.get('window');

export const DashboardScreen: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [totalSpent, setTotalSpent] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [agentsData, statsData] = await Promise.all([
        sardisApi.getAgents(),
        sardisApi.getQuickStats(),
      ]);

      setAgents(agentsData);
      setStats(statsData);

      const total = agentsData.reduce((sum, agent) => sum + agent.totalSpent, 0);
      setTotalSpent(total);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadDashboardData();
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'active':
        return colors.status.active;
      case 'paused':
        return colors.status.paused;
      case 'blocked':
        return colors.status.blocked;
      default:
        return colors.light.text.secondary;
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary.main} />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isRefreshing}
          onRefresh={onRefresh}
          tintColor={colors.primary.main}
        />
      }
    >
      {/* Total Spend Card */}
      <View style={styles.totalSpendCard}>
        <Text style={styles.totalSpendLabel}>Total Spending (30d)</Text>
        <Text style={styles.totalSpendAmount}>{formatCurrency(totalSpent)}</Text>
      </View>

      {/* Quick Stats */}
      {stats && (
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.activeAgents}</Text>
            <Text style={styles.statLabel}>Active Agents</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statValue}>{stats.activeCards}</Text>
            <Text style={styles.statLabel}>Active Cards</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={[styles.statValue, { color: colors.error }]}>
              {stats.blockedTransactions}
            </Text>
            <Text style={styles.statLabel}>Blocked</Text>
          </View>
        </View>
      )}

      {/* Active Agents */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Active Agents</Text>
        {agents.length === 0 ? (
          <Text style={styles.emptyText}>No agents found</Text>
        ) : (
          agents.map((agent) => {
            const utilization = (agent.totalSpent / agent.budgetLimit) * 100;
            return (
              <View key={agent.id} style={styles.agentCard}>
                <View style={styles.agentHeader}>
                  <View style={styles.agentInfo}>
                    <Text style={styles.agentName}>{agent.name}</Text>
                    <View style={[styles.statusBadge, { backgroundColor: getStatusColor(agent.status) }]}>
                      <Text style={styles.statusText}>{agent.status}</Text>
                    </View>
                  </View>
                  <Text style={styles.agentAmount}>
                    {formatCurrency(agent.totalSpent, agent.currency)}
                  </Text>
                </View>

                <View style={styles.budgetSection}>
                  <View style={styles.budgetInfo}>
                    <Text style={styles.budgetLabel}>
                      Budget: {formatCurrency(agent.budgetLimit, agent.currency)}
                    </Text>
                    <Text style={styles.budgetPercentage}>
                      {utilization.toFixed(1)}%
                    </Text>
                  </View>
                  <View style={styles.progressBar}>
                    <View
                      style={[
                        styles.progressFill,
                        {
                          width: `${Math.min(utilization, 100)}%`,
                          backgroundColor:
                            utilization > 90
                              ? colors.error
                              : utilization > 75
                              ? colors.warning
                              : colors.success,
                        },
                      ]}
                    />
                  </View>
                </View>

                <Text style={styles.lastActivity}>
                  Last activity: {new Date(agent.lastActivity).toLocaleString()}
                </Text>
              </View>
            );
          })
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.light.background,
  },
  content: {
    padding: 16,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.light.background,
  },
  totalSpendCard: {
    backgroundColor: colors.primary.main,
    borderRadius: 16,
    padding: 24,
    marginBottom: 16,
    shadowColor: colors.common.black,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  totalSpendLabel: {
    fontSize: 14,
    color: colors.primary.contrast,
    opacity: 0.9,
    marginBottom: 8,
  },
  totalSpendAmount: {
    fontSize: 36,
    fontWeight: '700',
    color: colors.primary.contrast,
  },
  statsRow: {
    flexDirection: 'row',
    marginBottom: 24,
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: colors.light.surface,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.light.border,
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.light.text.primary,
    marginBottom: 4,
  },
  statLabel: {
    fontSize: 12,
    color: colors.light.text.secondary,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.light.text.primary,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: colors.light.text.secondary,
    textAlign: 'center',
    paddingVertical: 24,
  },
  agentCard: {
    backgroundColor: colors.light.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.light.border,
  },
  agentHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  agentInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  agentName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.light.text.primary,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '600',
    color: colors.common.white,
    textTransform: 'uppercase',
  },
  agentAmount: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.light.text.primary,
  },
  budgetSection: {
    marginBottom: 8,
  },
  budgetInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  budgetLabel: {
    fontSize: 12,
    color: colors.light.text.secondary,
  },
  budgetPercentage: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.light.text.secondary,
  },
  progressBar: {
    height: 6,
    backgroundColor: colors.light.border,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  lastActivity: {
    fontSize: 11,
    color: colors.light.text.tertiary,
  },
});
