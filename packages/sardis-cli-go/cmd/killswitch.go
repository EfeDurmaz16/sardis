package cmd

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"

	"github.com/sardis-sh/sardis/packages/sardis-cli-go/internal/api"
)

var killSwitchCmd = &cobra.Command{
	Use:   "kill-switch",
	Short: "Manage the payment kill switch",
}

var killSwitchStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Check kill switch status",
	RunE:  runKillSwitchStatus,
}

var killSwitchActivateCmd = &cobra.Command{
	Use:   "activate",
	Short: "Activate kill switch (suspend all payments)",
	RunE:  runKillSwitchActivate,
}

var killSwitchDeactivateCmd = &cobra.Command{
	Use:   "deactivate",
	Short: "Deactivate kill switch (resume payments)",
	RunE:  runKillSwitchDeactivate,
}

func init() {
	rootCmd.AddCommand(killSwitchCmd)
	killSwitchCmd.AddCommand(killSwitchStatusCmd)
	killSwitchCmd.AddCommand(killSwitchActivateCmd)
	killSwitchCmd.AddCommand(killSwitchDeactivateCmd)

	killSwitchActivateCmd.Flags().String("scope", "global", "Scope: global, org, agent")
	killSwitchActivateCmd.Flags().String("scope-id", "", "Scope ID (org_id or agent_id)")
	killSwitchActivateCmd.Flags().String("reason", "manual_activation", "Reason for activation")

	killSwitchDeactivateCmd.Flags().String("scope", "global", "Scope: global, org, agent")
	killSwitchDeactivateCmd.Flags().String("scope-id", "", "Scope ID (org_id or agent_id)")
}

func runKillSwitchStatus(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	var health map[string]any
	if err := client.Get("/health", &health); err != nil {
		return err
	}

	components, ok := health["components"].(map[string]any)
	if !ok {
		fmt.Println("Kill switch status: unknown (not in health response)")
		return nil
	}

	ks, ok := components["kill_switch"].(map[string]any)
	if !ok {
		fmt.Println("Kill switch status: not configured")
		return nil
	}

	data, _ := json.MarshalIndent(ks, "", "  ")
	fmt.Printf("Kill Switch:\n%s\n", string(data))
	return nil
}

func runKillSwitchActivate(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	scope, _ := cmd.Flags().GetString("scope")
	scopeID, _ := cmd.Flags().GetString("scope-id")
	reason, _ := cmd.Flags().GetString("reason")

	body := map[string]string{
		"scope":    scope,
		"scope_id": scopeID,
		"reason":   reason,
	}

	var result map[string]any
	if err := client.Post("/api/v2/admin/kill-switch/activate", body, &result); err != nil {
		return fmt.Errorf("activate kill switch: %w", err)
	}

	fmt.Printf("Kill switch activated (scope=%s).\n", scope)
	return nil
}

func runKillSwitchDeactivate(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	scope, _ := cmd.Flags().GetString("scope")
	scopeID, _ := cmd.Flags().GetString("scope-id")

	body := map[string]string{
		"scope":    scope,
		"scope_id": scopeID,
	}

	var result map[string]any
	if err := client.Post("/api/v2/admin/kill-switch/deactivate", body, &result); err != nil {
		return fmt.Errorf("deactivate kill switch: %w", err)
	}

	fmt.Printf("Kill switch deactivated (scope=%s).\n", scope)
	return nil
}
