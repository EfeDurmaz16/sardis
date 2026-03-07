package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"

	"github.com/sardis-sh/sardis/packages/sardis-cli-go/internal/api"
)

var payCmd = &cobra.Command{
	Use:   "pay",
	Short: "Send a payment between agents",
	Long:  `Execute an agent-to-agent payment.`,
	RunE:  runPay,
}

func init() {
	rootCmd.AddCommand(payCmd)

	payCmd.Flags().String("from", "", "Sender agent ID")
	payCmd.Flags().String("to", "", "Recipient agent ID")
	payCmd.Flags().String("amount", "", "Payment amount")
	payCmd.Flags().String("token", "USDC", "Token type")
	payCmd.Flags().String("chain", "base", "Blockchain network")
	payCmd.Flags().String("memo", "", "Payment memo")

	_ = payCmd.MarkFlagRequired("from")
	_ = payCmd.MarkFlagRequired("to")
	_ = payCmd.MarkFlagRequired("amount")
}

func runPay(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	from, _ := cmd.Flags().GetString("from")
	to, _ := cmd.Flags().GetString("to")
	amount, _ := cmd.Flags().GetString("amount")
	token, _ := cmd.Flags().GetString("token")
	chain, _ := cmd.Flags().GetString("chain")
	memo, _ := cmd.Flags().GetString("memo")

	body := map[string]string{
		"sender_agent_id":    from,
		"recipient_agent_id": to,
		"amount":             amount,
		"token":              token,
		"chain":              chain,
	}
	if memo != "" {
		body["memo"] = memo
	}

	fmt.Printf("Sending %s %s from %s to %s on %s...\n", amount, token, from, to, chain)

	var result map[string]any
	if err := client.Post("/api/v2/a2a/pay", body, &result); err != nil {
		return fmt.Errorf("payment failed: %w", err)
	}

	if txHash, ok := result["tx_hash"].(string); ok {
		fmt.Printf("Payment submitted. tx_hash: %s\n", txHash)
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
	return nil
}
