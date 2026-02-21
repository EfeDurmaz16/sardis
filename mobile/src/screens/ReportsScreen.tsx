import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Share,
} from 'react-native';
import { colors } from '../theme/colors';
import { sardisApi } from '../api/sardisApi';
import { SpendingSummary } from '../types';

type Period = '7d' | '30d' | '90d';

export const ReportsScreen: React.FC = () => {
  const [summary, setSummary] = useState<SpendingSummary | null>(null);
  const [period, setPeriod] = useState<Period>('30d');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    loadSummary();
  }, [period]);

  const loadSummary = async () => {
    try {
      const data = await sardisApi.getSpendingSummary(period);
      setSummary(data);
    } catch (error) {
      console.error('Failed to load summary:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadSummary();
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await sardisApi.exportReport(period, 'csv');

      // In a real app, you'd use a library like react-native-fs or expo-file-system
      // to save and share the file. For now, we'll just show a share dialog.
      await Share.share({
        message: 'Spending report exported successfully',
        title: `Sardis Spending Report - ${period}`,
      });
    } catch (error) {
      console.error('Failed to export report:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const getPeriodLabel = (p: Period) => {
    switch (p) {
      case '7d':
        return 'Last 7 Days';
      case '30d':
        return 'Last 30 Days';
      case '90d':
        return 'Last 90 Days';
    }
  };

  const renderPeriodButton = (p: Period) => {
    const isActive = period === p;
    return (
      <TouchableOpacity
        key={p}
        style={[styles.periodButton, isActive && styles.periodButtonActive]}
        onPress={() => setPeriod(p)}
      >
        <Text style={[styles.periodText, isActive && styles.periodTextActive]}>
          {getPeriodLabel(p)}
        </Text>
      </TouchableOpacity>
    );
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary.main} />
      </View>
    );
  }

  if (!summary) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.emptyText}>No data available</Text>
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
      {/* Period Selector */}
      <View style={styles.periodSelector}>
        {(['7d', '30d', '90d'] as Period[]).map(renderPeriodButton)}
      </View>

      {/* Total Spending */}
      <View style={styles.totalCard}>
        <Text style={styles.totalLabel}>Total Spending</Text>
        <Text style={styles.totalAmount}>
          {formatCurrency(summary.totalSpent, summary.currency)}
        </Text>
      </View>

      {/* Agent Breakdown */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>By Agent</Text>
        {summary.agentBreakdown.map((item, index) => (
          <View key={index} style={styles.breakdownItem}>
            <View style={styles.breakdownInfo}>
              <Text style={styles.breakdownName}>{item.agentName}</Text>
              <Text style={styles.breakdownPercentage}>
                {item.percentage.toFixed(1)}%
              </Text>
            </View>
            <View style={styles.breakdownBar}>
              <View
                style={[
                  styles.breakdownFill,
                  {
                    width: `${item.percentage}%`,
                    backgroundColor: colors.primary.main,
                  },
                ]}
              />
            </View>
            <Text style={styles.breakdownAmount}>
              {formatCurrency(item.amount, summary.currency)}
            </Text>
          </View>
        ))}
      </View>

      {/* Category Breakdown */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>By Category</Text>
        {summary.categoryBreakdown.map((item, index) => (
          <View key={index} style={styles.breakdownItem}>
            <View style={styles.breakdownInfo}>
              <Text style={styles.breakdownName}>{item.category}</Text>
              <Text style={styles.breakdownPercentage}>
                {item.percentage.toFixed(1)}%
              </Text>
            </View>
            <View style={styles.breakdownBar}>
              <View
                style={[
                  styles.breakdownFill,
                  {
                    width: `${item.percentage}%`,
                    backgroundColor: colors.accent.main,
                  },
                ]}
              />
            </View>
            <Text style={styles.breakdownAmount}>
              {formatCurrency(item.amount, summary.currency)}
            </Text>
          </View>
        ))}
      </View>

      {/* Daily Spending (Mini Chart) */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Daily Trend</Text>
        <View style={styles.chartContainer}>
          {summary.dailySpending.map((day, index) => {
            const maxAmount = Math.max(...summary.dailySpending.map(d => d.amount));
            const height = maxAmount > 0 ? (day.amount / maxAmount) * 100 : 0;

            return (
              <View key={index} style={styles.chartBar}>
                <View style={styles.chartBarContainer}>
                  <View
                    style={[
                      styles.chartBarFill,
                      {
                        height: `${height}%`,
                        backgroundColor: colors.primary.main,
                      },
                    ]}
                  />
                </View>
                <Text style={styles.chartLabel}>
                  {new Date(day.date).getDate()}
                </Text>
              </View>
            );
          })}
        </View>
      </View>

      {/* Export Button */}
      <TouchableOpacity
        style={styles.exportButton}
        onPress={handleExport}
        disabled={isExporting}
      >
        <Text style={styles.exportButtonText}>
          {isExporting ? 'Exporting...' : 'Export Report'}
        </Text>
      </TouchableOpacity>
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
  emptyText: {
    fontSize: 14,
    color: colors.light.text.secondary,
  },
  periodSelector: {
    flexDirection: 'row',
    marginBottom: 16,
    gap: 8,
  },
  periodButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: colors.light.surface,
    borderWidth: 1,
    borderColor: colors.light.border,
    alignItems: 'center',
  },
  periodButtonActive: {
    backgroundColor: colors.primary.main,
    borderColor: colors.primary.main,
  },
  periodText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.light.text.secondary,
  },
  periodTextActive: {
    color: colors.primary.contrast,
  },
  totalCard: {
    backgroundColor: colors.primary.main,
    borderRadius: 16,
    padding: 24,
    marginBottom: 24,
    shadowColor: colors.common.black,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  totalLabel: {
    fontSize: 14,
    color: colors.primary.contrast,
    opacity: 0.9,
    marginBottom: 8,
  },
  totalAmount: {
    fontSize: 36,
    fontWeight: '700',
    color: colors.primary.contrast,
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
  breakdownItem: {
    marginBottom: 16,
  },
  breakdownInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  breakdownName: {
    fontSize: 14,
    color: colors.light.text.primary,
  },
  breakdownPercentage: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.light.text.secondary,
  },
  breakdownBar: {
    height: 8,
    backgroundColor: colors.light.border,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 4,
  },
  breakdownFill: {
    height: '100%',
    borderRadius: 4,
  },
  breakdownAmount: {
    fontSize: 12,
    color: colors.light.text.tertiary,
  },
  chartContainer: {
    flexDirection: 'row',
    height: 120,
    alignItems: 'flex-end',
    gap: 4,
    paddingVertical: 8,
  },
  chartBar: {
    flex: 1,
    alignItems: 'center',
  },
  chartBarContainer: {
    flex: 1,
    width: '100%',
    justifyContent: 'flex-end',
  },
  chartBarFill: {
    width: '100%',
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  chartLabel: {
    fontSize: 10,
    color: colors.light.text.tertiary,
    marginTop: 4,
  },
  exportButton: {
    backgroundColor: colors.primary.main,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 24,
  },
  exportButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.primary.contrast,
  },
});
