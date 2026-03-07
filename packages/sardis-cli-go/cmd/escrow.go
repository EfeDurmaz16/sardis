package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/api"
)

var escrowCmd = &cobra.Command{
	Use:   "escrow",
	Short: "Manage escrow payments",
}

var escrowCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new escrow",
	RunE:  runEscrowCreate,
}

var escrowFundCmd = &cobra.Command{
	Use:   "fund [escrow_id]",
	Short: "Fund an escrow",
	Args:  cobra.ExactArgs(1),
	RunE:  runEscrowFund,
}

var escrowReleaseCmd = &cobra.Command{
	Use:   "release [escrow_id]",
	Short: "Release escrow funds to payee",
	Args:  cobra.ExactArgs(1),
	RunE:  runEscrowRelease,
}

var escrowRefundCmd = &cobra.Command{
	Use:   "refund [escrow_id]",
	Short: "Refund escrow to payer",
	Args:  cobra.ExactArgs(1),
	RunE:  runEscrowRefund,
}

var escrowStatusCmd = &cobra.Command{
	Use:   "status [escrow_id]",
	Short: "Check escrow status",
	Args:  cobra.ExactArgs(1),
	RunE:  runEscrowStatus,
}

func init() {
	rootCmd.AddCommand(escrowCmd)
	escrowCmd.AddCommand(escrowCreateCmd)
	escrowCmd.AddCommand(escrowFundCmd)
	escrowCmd.AddCommand(escrowReleaseCmd)
	escrowCmd.AddCommand(escrowRefundCmd)
	escrowCmd.AddCommand(escrowStatusCmd)

	escrowCreateCmd.Flags().String("payer", "", "Payer agent ID")
	escrowCreateCmd.Flags().String("payee", "", "Payee agent ID")
	escrowCreateCmd.Flags().String("amount", "", "Escrow amount")
	escrowCreateCmd.Flags().String("token", "USDC", "Token type")
	escrowCreateCmd.Flags().String("chain", "base", "Blockchain network")
	escrowCreateCmd.Flags().Int("timeout", 24, "Timeout in hours")
	_ = escrowCreateCmd.MarkFlagRequired("payer")
	_ = escrowCreateCmd.MarkFlagRequired("payee")
	_ = escrowCreateCmd.MarkFlagRequired("amount")

	escrowFundCmd.Flags().String("tx-hash", "", "Funding transaction hash")
	_ = escrowFundCmd.MarkFlagRequired("tx-hash")

	escrowRefundCmd.Flags().String("reason", "", "Refund reason")
}

func runEscrowCreate(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	payer, _ := cmd.Flags().GetString("payer")
	payee, _ := cmd.Flags().GetString("payee")
	amount, _ := cmd.Flags().GetString("amount")
	token, _ := cmd.Flags().GetString("token")
	chain, _ := cmd.Flags().GetString("chain")
	timeout, _ := cmd.Flags().GetInt("timeout")

	body := map[string]any{
		"payer_agent_id": payer,
		"payee_agent_id": payee,
		"amount":         amount,
		"token":          token,
		"chain":          chain,
		"timeout_hours":  timeout,
	}

	var result map[string]any
	if err := client.Post("/api/v2/a2a/escrows", body, &result); err != nil {
		return err
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
	return nil
}

func runEscrowFund(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	escrowID := args[0]
	txHash, _ := cmd.Flags().GetString("tx-hash")

	body := map[string]string{"tx_hash": txHash}

	var result map[string]any
	if err := client.Post(fmt.Sprintf("/api/v2/a2a/escrows/%s/fund", escrowID), body, &result); err != nil {
		return err
	}

	fmt.Printf("Escrow %s funded.\n", escrowID)
	return nil
}

func runEscrowRelease(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	escrowID := args[0]

	var result map[string]any
	if err := client.Post(fmt.Sprintf("/api/v2/a2a/escrows/%s/release", escrowID), nil, &result); err != nil {
		return err
	}

	fmt.Printf("Escrow %s released.\n", escrowID)
	return nil
}

func runEscrowRefund(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	escrowID := args[0]
	reason, _ := cmd.Flags().GetString("reason")

	body := map[string]string{"reason": reason}

	var result map[string]any
	if err := client.Post(fmt.Sprintf("/api/v2/a2a/escrows/%s/refund", escrowID), body, &result); err != nil {
		return err
	}

	fmt.Printf("Escrow %s refunded.\n", escrowID)
	return nil
}

func runEscrowStatus(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	escrowID := args[0]

	var result map[string]any
	if err := client.Get(fmt.Sprintf("/api/v2/a2a/escrows/%s/status", escrowID), &result); err != nil {
		return err
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
	return nil
}
