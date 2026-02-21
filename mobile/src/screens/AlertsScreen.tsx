import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { colors } from '../theme/colors';
import { sardisApi } from '../api/sardisApi';
import { Alert } from '../types';

type SeverityFilter = 'all' | 'info' | 'warning' | 'critical';

export const AlertsScreen: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filteredAlerts, setFilteredAlerts] = useState<Alert[]>([]);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadAlerts();
  }, []);

  useEffect(() => {
    filterAlerts();
  }, [alerts, severityFilter]);

  const loadAlerts = async () => {
    try {
      const data = await sardisApi.getAlerts();
      setAlerts(data);
    } catch (error) {
      console.error('Failed to load alerts:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const filterAlerts = () => {
    if (severityFilter === 'all') {
      setFilteredAlerts(alerts);
    } else {
      setFilteredAlerts(alerts.filter(alert => alert.severity === severityFilter));
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadAlerts();
  };

  const handleAlertPress = async (alert: Alert) => {
    if (!alert.read) {
      try {
        await sardisApi.markAlertAsRead(alert.id);
        setAlerts(prev =>
          prev.map(a => (a.id === alert.id ? { ...a, read: true } : a))
        );
      } catch (error) {
        console.error('Failed to mark alert as read:', error);
      }
    }
  };

  const getSeverityColor = (severity: Alert['severity']) => {
    return colors.severity[severity];
  };

  const renderFilterButton = (filter: SeverityFilter, label: string) => {
    const isActive = severityFilter === filter;
    return (
      <TouchableOpacity
        style={[styles.filterButton, isActive && styles.filterButtonActive]}
        onPress={() => setSeverityFilter(filter)}
      >
        <Text style={[styles.filterText, isActive && styles.filterTextActive]}>
          {label}
        </Text>
      </TouchableOpacity>
    );
  };

  const renderAlert = ({ item }: { item: Alert }) => {
    return (
      <TouchableOpacity
        style={[styles.alertCard, !item.read && styles.alertCardUnread]}
        onPress={() => handleAlertPress(item)}
        activeOpacity={0.7}
      >
        <View style={styles.alertHeader}>
          <View
            style={[
              styles.severityIndicator,
              { backgroundColor: getSeverityColor(item.severity) },
            ]}
          />
          <View style={styles.alertInfo}>
            <View style={styles.alertTitleRow}>
              <Text style={styles.agentName}>{item.agentName}</Text>
              {!item.read && <View style={styles.unreadDot} />}
            </View>
            <Text style={styles.alertMessage}>{item.message}</Text>
            <Text style={styles.alertTimestamp}>
              {new Date(item.timestamp).toLocaleString()}
            </Text>
          </View>
        </View>
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

  return (
    <View style={styles.container}>
      <View style={styles.filterContainer}>
        {renderFilterButton('all', 'All')}
        {renderFilterButton('info', 'Info')}
        {renderFilterButton('warning', 'Warning')}
        {renderFilterButton('critical', 'Critical')}
      </View>

      <FlatList
        data={filteredAlerts}
        renderItem={renderAlert}
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
            <Text style={styles.emptyText}>No alerts to display</Text>
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
  filterContainer: {
    flexDirection: 'row',
    padding: 16,
    gap: 8,
    backgroundColor: colors.light.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.light.border,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.light.border,
    backgroundColor: colors.common.white,
  },
  filterButtonActive: {
    backgroundColor: colors.primary.main,
    borderColor: colors.primary.main,
  },
  filterText: {
    fontSize: 14,
    color: colors.light.text.secondary,
    fontWeight: '500',
  },
  filterTextActive: {
    color: colors.primary.contrast,
  },
  listContent: {
    padding: 16,
  },
  alertCard: {
    backgroundColor: colors.light.surface,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.light.border,
    overflow: 'hidden',
  },
  alertCardUnread: {
    borderLeftWidth: 4,
    borderLeftColor: colors.primary.main,
  },
  alertHeader: {
    flexDirection: 'row',
  },
  severityIndicator: {
    width: 4,
  },
  alertInfo: {
    flex: 1,
    padding: 16,
  },
  alertTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  agentName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.light.text.primary,
    flex: 1,
  },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primary.main,
    marginLeft: 8,
  },
  alertMessage: {
    fontSize: 14,
    color: colors.light.text.primary,
    marginBottom: 8,
    lineHeight: 20,
  },
  alertTimestamp: {
    fontSize: 12,
    color: colors.light.text.tertiary,
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
