import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Modal,
  Alert as RNAlert,
} from 'react-native';
import { colors } from '../theme/colors';
import { sardisApi } from '../api/sardisApi';
import { ApprovalRequest } from '../types';

export const ApprovalScreen: React.FC = () => {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    loadApprovalRequests();
  }, []);

  const loadApprovalRequests = async () => {
    try {
      const data = await sardisApi.getApprovalRequests('pending');
      setRequests(data);
    } catch (error) {
      console.error('Failed to load approval requests:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const onRefresh = () => {
    setIsRefreshing(true);
    loadApprovalRequests();
  };

  const handleApprove = async (request: ApprovalRequest) => {
    RNAlert.alert(
      'Approve Transaction',
      `Approve ${formatCurrency(request.amount, request.currency)} payment to ${request.merchant}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Approve',
          style: 'default',
          onPress: async () => {
            setIsProcessing(true);
            try {
              await sardisApi.approveTransaction(request.id);
              setRequests(prev => prev.filter(r => r.id !== request.id));
              setSelectedRequest(null);
              RNAlert.alert('Success', 'Transaction approved');
            } catch (error) {
              RNAlert.alert('Error', 'Failed to approve transaction');
            } finally {
              setIsProcessing(false);
            }
          },
        },
      ]
    );
  };

  const handleReject = async (request: ApprovalRequest) => {
    RNAlert.alert(
      'Reject Transaction',
      `Reject ${formatCurrency(request.amount, request.currency)} payment to ${request.merchant}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reject',
          style: 'destructive',
          onPress: async () => {
            setIsProcessing(true);
            try {
              await sardisApi.rejectTransaction(request.id, 'Rejected by user');
              setRequests(prev => prev.filter(r => r.id !== request.id));
              setSelectedRequest(null);
              RNAlert.alert('Success', 'Transaction rejected');
            } catch (error) {
              RNAlert.alert('Error', 'Failed to reject transaction');
            } finally {
              setIsProcessing(false);
            }
          },
        },
      ]
    );
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const renderRequest = ({ item }: { item: ApprovalRequest }) => {
    return (
      <TouchableOpacity
        style={styles.requestCard}
        onPress={() => setSelectedRequest(item)}
        activeOpacity={0.7}
      >
        <View style={styles.requestHeader}>
          <View style={styles.requestInfo}>
            <Text style={styles.agentName}>{item.agentName}</Text>
            <Text style={styles.merchant}>{item.merchant}</Text>
          </View>
          <Text style={styles.amount}>
            {formatCurrency(item.amount, item.currency)}
          </Text>
        </View>

        {item.policyViolation && (
          <View style={styles.violationBadge}>
            <Text style={styles.violationText}>Policy Violation</Text>
          </View>
        )}

        <View style={styles.requestDetails}>
          <Text style={styles.detailLabel}>Category: {item.category}</Text>
          <Text style={styles.detailLabel}>
            {new Date(item.timestamp).toLocaleString()}
          </Text>
        </View>

        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.actionButton, styles.rejectButton]}
            onPress={() => handleReject(item)}
            disabled={isProcessing}
          >
            <Text style={styles.rejectButtonText}>Reject</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, styles.approveButton]}
            onPress={() => handleApprove(item)}
            disabled={isProcessing}
          >
            <Text style={styles.approveButtonText}>Approve</Text>
          </TouchableOpacity>
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
      <FlatList
        data={requests}
        renderItem={renderRequest}
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
            <Text style={styles.emptyText}>No pending approvals</Text>
          </View>
        }
      />

      {/* Detail Modal */}
      <Modal
        visible={!!selectedRequest}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setSelectedRequest(null)}
      >
        {selectedRequest && (
          <View style={styles.modalContainer}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Transaction Details</Text>
              <TouchableOpacity onPress={() => setSelectedRequest(null)}>
                <Text style={styles.modalClose}>Close</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.modalContent}>
              <View style={styles.detailRow}>
                <Text style={styles.detailRowLabel}>Agent</Text>
                <Text style={styles.detailRowValue}>{selectedRequest.agentName}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailRowLabel}>Amount</Text>
                <Text style={styles.detailRowValue}>
                  {formatCurrency(selectedRequest.amount, selectedRequest.currency)}
                </Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailRowLabel}>Merchant</Text>
                <Text style={styles.detailRowValue}>{selectedRequest.merchant}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailRowLabel}>Category</Text>
                <Text style={styles.detailRowValue}>{selectedRequest.category}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailRowLabel}>Time</Text>
                <Text style={styles.detailRowValue}>
                  {new Date(selectedRequest.timestamp).toLocaleString()}
                </Text>
              </View>

              {selectedRequest.policyViolation && (
                <View style={[styles.detailRow, styles.violationRow]}>
                  <Text style={styles.detailRowLabel}>Policy Violation</Text>
                  <Text style={[styles.detailRowValue, styles.violationValue]}>
                    {selectedRequest.policyViolation}
                  </Text>
                </View>
              )}

              {selectedRequest.transactionDetails && (
                <>
                  <Text style={styles.sectionTitle}>Transaction Details</Text>
                  {selectedRequest.transactionDetails.chain && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailRowLabel}>Chain</Text>
                      <Text style={styles.detailRowValue}>
                        {selectedRequest.transactionDetails.chain}
                      </Text>
                    </View>
                  )}
                  {selectedRequest.transactionDetails.token && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailRowLabel}>Token</Text>
                      <Text style={styles.detailRowValue}>
                        {selectedRequest.transactionDetails.token}
                      </Text>
                    </View>
                  )}
                  {selectedRequest.transactionDetails.recipient && (
                    <View style={styles.detailRow}>
                      <Text style={styles.detailRowLabel}>Recipient</Text>
                      <Text style={[styles.detailRowValue, styles.monoText]} numberOfLines={1}>
                        {selectedRequest.transactionDetails.recipient}
                      </Text>
                    </View>
                  )}
                </>
              )}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalRejectButton]}
                onPress={() => handleReject(selectedRequest)}
                disabled={isProcessing}
              >
                <Text style={styles.modalRejectButtonText}>
                  {isProcessing ? 'Processing...' : 'Reject'}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalApproveButton]}
                onPress={() => handleApprove(selectedRequest)}
                disabled={isProcessing}
              >
                <Text style={styles.modalApproveButtonText}>
                  {isProcessing ? 'Processing...' : 'Approve'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </Modal>
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
  requestCard: {
    backgroundColor: colors.light.surface,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.light.border,
  },
  requestHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  requestInfo: {
    flex: 1,
  },
  agentName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.light.text.primary,
    marginBottom: 4,
  },
  merchant: {
    fontSize: 14,
    color: colors.light.text.secondary,
  },
  amount: {
    fontSize: 18,
    fontWeight: '700',
    color: colors.light.text.primary,
  },
  violationBadge: {
    backgroundColor: colors.error,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  violationText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.common.white,
  },
  requestDetails: {
    marginBottom: 16,
  },
  detailLabel: {
    fontSize: 12,
    color: colors.light.text.tertiary,
    marginBottom: 4,
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  rejectButton: {
    backgroundColor: colors.light.surface,
    borderWidth: 1,
    borderColor: colors.error,
  },
  rejectButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.error,
  },
  approveButton: {
    backgroundColor: colors.success,
  },
  approveButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.common.white,
  },
  emptyContainer: {
    paddingVertical: 48,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    color: colors.light.text.secondary,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: colors.light.background,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.light.border,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.light.text.primary,
  },
  modalClose: {
    fontSize: 16,
    color: colors.primary.main,
  },
  modalContent: {
    flex: 1,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.light.text.primary,
    marginTop: 24,
    marginBottom: 12,
  },
  detailRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.light.border,
  },
  detailRowLabel: {
    fontSize: 12,
    color: colors.light.text.secondary,
    marginBottom: 4,
  },
  detailRowValue: {
    fontSize: 16,
    color: colors.light.text.primary,
  },
  violationRow: {
    backgroundColor: colors.error + '10',
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  violationValue: {
    color: colors.error,
    fontWeight: '500',
  },
  monoText: {
    fontFamily: 'monospace',
    fontSize: 14,
  },
  modalActions: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
    borderTopWidth: 1,
    borderTopColor: colors.light.border,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  modalRejectButton: {
    backgroundColor: colors.light.surface,
    borderWidth: 1,
    borderColor: colors.error,
  },
  modalRejectButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.error,
  },
  modalApproveButton: {
    backgroundColor: colors.success,
  },
  modalApproveButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.common.white,
  },
});
