package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/sardis-sh/sardis/packages/sardis-cli-go/internal/api"
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show account and system status",
	RunE:  runStatus,
}

func init() {
	rootCmd.AddCommand(statusCmd)
}

func runStatus(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	var health map[string]any
	if err := client.Get("/health", &health); err != nil {
		return fmt.Errorf("health check: %w", err)
	}

	fmt.Println("=== Sardis Platform Status ===")
	if s, ok := health["status"].(string); ok {
		fmt.Printf("  Status:      %s\n", s)
	}
	if v, ok := health["version"].(string); ok {
		fmt.Printf("  Version:     %s\n", v)
	}
	if e, ok := health["environment"].(string); ok {
		fmt.Printf("  Environment: %s\n", e)
	}
	if cm, ok := health["chain_mode"].(string); ok {
		fmt.Printf("  Chain Mode:  %s\n", cm)
	}

	if components, ok := health["components"].(map[string]any); ok {
		fmt.Println("\n  Components:")
		for name, comp := range components {
			if c, ok := comp.(map[string]any); ok {
				if s, ok := c["status"].(string); ok {
					fmt.Printf("    %-20s %s\n", name+":", s)
				}
			}
		}
	}

	return nil
}
