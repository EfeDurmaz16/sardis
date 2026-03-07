package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"text/tabwriter"

	"github.com/spf13/cobra"

	"github.com/sardis-sh/sardis/packages/sardis-cli-go/internal/api"
)

var walletsCmd = &cobra.Command{
	Use:   "wallets",
	Short: "Manage wallets",
}

var walletsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all wallets",
	RunE:  runWalletsList,
}

var walletsCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new wallet",
	RunE:  runWalletsCreate,
}

var walletsBalanceCmd = &cobra.Command{
	Use:   "balance [wallet_id]",
	Short: "Get wallet balance",
	Args:  cobra.ExactArgs(1),
	RunE:  runWalletsBalance,
}

func init() {
	rootCmd.AddCommand(walletsCmd)
	walletsCmd.AddCommand(walletsListCmd)
	walletsCmd.AddCommand(walletsCreateCmd)
	walletsCmd.AddCommand(walletsBalanceCmd)

	walletsCreateCmd.Flags().String("agent-id", "", "Agent ID to assign wallet to")
	walletsCreateCmd.Flags().String("chain", "base", "Blockchain network")
	_ = walletsCreateCmd.MarkFlagRequired("agent-id")
}

func runWalletsList(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	var result struct {
		Wallets []json.RawMessage `json:"wallets"`
	}
	if err := client.Get("/api/v2/wallets", &result); err != nil {
		return err
	}

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tAGENT\tCHAIN\tADDRESS\tSTATUS")
	for _, raw := range result.Wallets {
		var wl map[string]any
		_ = json.Unmarshal(raw, &wl)
		fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%s\n",
			strOrDash(wl, "wallet_id"),
			strOrDash(wl, "agent_id"),
			strOrDash(wl, "chain"),
			strOrDash(wl, "address"),
			strOrDash(wl, "status"),
		)
	}
	return w.Flush()
}

func runWalletsCreate(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	agentID, _ := cmd.Flags().GetString("agent-id")
	chain, _ := cmd.Flags().GetString("chain")

	body := map[string]string{"agent_id": agentID, "chain": chain}

	var result map[string]any
	if err := client.Post("/api/v2/wallets", body, &result); err != nil {
		return err
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
	return nil
}

func runWalletsBalance(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	walletID := args[0]

	var result map[string]any
	if err := client.Get(fmt.Sprintf("/api/v2/wallets/%s/balance", walletID), &result); err != nil {
		return err
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
	return nil
}
