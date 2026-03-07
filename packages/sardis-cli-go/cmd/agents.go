package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"text/tabwriter"

	"github.com/spf13/cobra"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/api"
)

var agentsCmd = &cobra.Command{
	Use:   "agents",
	Short: "Manage AI agents",
}

var agentsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all agents",
	RunE:  runAgentsList,
}

var agentsCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new agent",
	RunE:  runAgentsCreate,
}

var agentsFreezeCmd = &cobra.Command{
	Use:   "freeze [agent_id]",
	Short: "Freeze an agent",
	Args:  cobra.ExactArgs(1),
	RunE:  runAgentsFreeze,
}

func init() {
	rootCmd.AddCommand(agentsCmd)
	agentsCmd.AddCommand(agentsListCmd)
	agentsCmd.AddCommand(agentsCreateCmd)
	agentsCmd.AddCommand(agentsFreezeCmd)

	agentsCreateCmd.Flags().String("name", "", "Agent name")
	agentsCreateCmd.Flags().String("type", "payment", "Agent type")
	_ = agentsCreateCmd.MarkFlagRequired("name")
}

func runAgentsList(cmd *cobra.Command, args []string) error {
	client := api.NewClient()

	var result struct {
		Agents []json.RawMessage `json:"agents"`
	}
	if err := client.Get("/api/v2/agents", &result); err != nil {
		return err
	}

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tNAME\tTYPE\tSTATUS")
	for _, raw := range result.Agents {
		var a map[string]any
		_ = json.Unmarshal(raw, &a)
		fmt.Fprintf(w, "%s\t%s\t%s\t%s\n",
			strOrDash(a, "agent_id"),
			strOrDash(a, "name"),
			strOrDash(a, "agent_type"),
			strOrDash(a, "status"),
		)
	}
	return w.Flush()
}

func runAgentsCreate(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	name, _ := cmd.Flags().GetString("name")
	agentType, _ := cmd.Flags().GetString("type")

	body := map[string]string{"name": name, "agent_type": agentType}

	var result map[string]any
	if err := client.Post("/api/v2/agents", body, &result); err != nil {
		return err
	}

	data, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println(string(data))
	return nil
}

func runAgentsFreeze(cmd *cobra.Command, args []string) error {
	client := api.NewClient()
	agentID := args[0]

	var result map[string]any
	if err := client.Post(fmt.Sprintf("/api/v2/agents/%s/freeze", agentID), nil, &result); err != nil {
		return err
	}

	fmt.Printf("Agent %s frozen.\n", agentID)
	return nil
}

func strOrDash(m map[string]any, key string) string {
	if v, ok := m[key].(string); ok && v != "" {
		return v
	}
	return "-"
}
