package cmd

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/api"
	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/tui"
)

var dashboardCmd = &cobra.Command{
	Use:   "dashboard",
	Short: "Interactive TUI dashboard",
	Long:  `Launch the interactive terminal dashboard with real-time overview of agents, wallets, and transactions.`,
	RunE:  runDashboard,
}

func init() {
	rootCmd.AddCommand(dashboardCmd)
}

func runDashboard(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	model := tui.New(client)

	p := tea.NewProgram(model, tea.WithAltScreen())
	if _, err := p.Run(); err != nil {
		return fmt.Errorf("dashboard error: %w", err)
	}

	return nil
}
