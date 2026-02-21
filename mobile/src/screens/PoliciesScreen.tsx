import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  Switch,
} from 'react-native';
import { colors } from '../theme/colors';
import { sardisApi } from '../api/sardisApi';
import { SpendingPolicy } from '../types';

export const PoliciesScreen: React.FC = () => {
  const [policies, setPolicies] = useState<SpendingPolicy[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadPolicies();
  }, []);

  const loadPolicies = async () => {
    try {
      const data = await sardisApi.getPolicies();
      setPolicies(data);
    } catch (error) {
      console.error('Failed to load policies:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadPolicies();
  };

  const handleTogglePolicy = async (policy: SpendingPolicy) => {
    const newEnabledState = !policy.enabled;

    // Optimistic update
    setPolicies(prev =>
      prev.map(p => (p.id === policy.id ? { ...p, enabled: newEnabledState } : p))
    );

    try {
      await sardisApi.togglePolicy(policy.id, newEnabledState);
    } catch (error) {
      console.error('Failed to toggle policy:', error);
      // Revert on error
      setPolicies(prev =>
        prev.map(p => (p.id === policy.id ? { ...p, enabled: policy.enabled } : p))
      );
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const renderPolicy = ({ item }: { item: SpendingPolicy }) => {
    return (
      <View style={styles.policyCard}>
        <View style={styles.policyHeader}>
          <View style={styles.policyInfo}>
            <Text style={styles.agentName}>{item.agentName}</Text>
            <View style={[styles.statusBadge, item.enabled ? styles.statusActive : styles.statusDisabled]}>
              <Text style={styles.statusText}>
                {item.enabled ? 'Active' : 'Disabled'}
              </Text>
            </View>
          </View>
          <Switch
            value={item.enabled}
            onValueChange={() => handleTogglePolicy(item)}
            trackColor={{ false: colors.light.border, true: colors.success }}
            thumbColor={colors.common.white}
          />
        </View>

        <View style={styles.limitsSection}>
          {item.dailyLimit && (
            <View style={styles.limitRow}>
              <Text style={styles.limitLabel}>Daily Limit</Text>
              <Text style={styles.limitValue}>
                {formatCurrency(item.dailyLimit, item.currency)}
              </Text>
            </View>
          )}
          {item.monthlyLimit && (
            <View style={styles.limitRow}>
              <Text style={styles.limitLabel}>Monthly Limit</Text>
              <Text style={styles.limitValue}>
                {formatCurrency(item.monthlyLimit, item.currency)}
              </Text>
            </View>
          )}
          {item.requireApprovalAbove && (
            <View style={styles.limitRow}>
              <Text style={styles.limitLabel}>Requires Approval Above</Text>
              <Text style={styles.limitValue}>
                {formatCurrency(item.requireApprovalAbove, item.currency)}
              </Text>
            </View>
          )}
        </View>

        {item.allowedCategories && item.allowedCategories.length > 0 && (
          <View style={styles.categoriesSection}>
            <Text style={styles.sectionLabel}>Allowed Categories</Text>
            <View style={styles.tagsContainer}>
              {item.allowedCategories.map((category, index) => (
                <View key={index} style={styles.tag}>
                  <Text style={styles.tagText}>{category}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {item.blockedMerchants && item.blockedMerchants.length > 0 && (
          <View style={styles.categoriesSection}>
            <Text style={styles.sectionLabel}>Blocked Merchants</Text>
            <View style={styles.tagsContainer}>
              {item.blockedMerchants.map((merchant, index) => (
                <View key={index} style={[styles.tag, styles.tagBlocked]}>
                  <Text style={[styles.tagText, styles.tagTextBlocked]}>{merchant}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </View>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary.main} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={policies}
        renderItem={renderPolicy}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={onRefresh}
            tintColor={colors.primary.main}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No policies configured</Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.light.background,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.light.background,
  },
  listContent: {
    padding: 16,
  },
  policyCard: {
    backgroundColor: colors.light.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.light.border,
  },
  policyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  policyInfo: {
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
  statusActive: {
    backgroundColor: colors.success,
  },
  statusDisabled: {
    backgroundColor: colors.light.text.tertiary,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '600',
    color: colors.common.white,
    textTransform: 'uppercase',
  },
  limitsSection: {
    marginBottom: 12,
  },
  limitRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.light.border,
  },
  limitLabel: {
    fontSize: 14,
    color: colors.light.text.secondary,
  },
  limitValue: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.light.text.primary,
  },
  categoriesSection: {
    marginTop: 12,
  },
  sectionLabel: {
    fontSize: 12,
    color: colors.light.text.secondary,
    marginBottom: 8,
    textTransform: 'uppercase',
    fontWeight: '600',
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  tag: {
    backgroundColor: colors.primary.main + '20',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  tagBlocked: {
    backgroundColor: colors.error + '20',
  },
  tagText: {
    fontSize: 12,
    color: colors.primary.main,
    fontWeight: '500',
  },
  tagTextBlocked: {
    color: colors.error,
  },
  emptyContainer: {
    paddingVertical: 48,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    color: colors.light.text.secondary,
  },
});
