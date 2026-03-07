package tui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/api"
)

// Tab identifiers
const (
	TabOverview      = 0
	TabAgents        = 1
	TabWallets       = 2
	TabTransactions  = 3
)

var tabNames = []string{"Overview", "Agents", "Wallets", "Transactions"}

// Model is the Bubble Tea model for the dashboard.
type Model struct {
	client     *api.Client
	activeTab  int
	width      int
	height     int
	quitting   bool

	// Data
	health       map[string]any
	agents       []map[string]any
	wallets      []map[string]any
	transactions []map[string]any
	err          error
	loading      bool
	filter       string
	filtering    bool
}

// New creates a new dashboard model.
func New(client *api.Client) Model {
	return Model{
		client:  client,
		loading: true,
	}
}

// Messages
type healthMsg struct{ data map[string]any }
type agentsMsg struct{ data []map[string]any }
type walletsMsg struct{ data []map[string]any }
type errMsg struct{ err error }

// Init starts the initial data fetch.
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		fetchHealth(m.client),
		fetchAgents(m.client),
		fetchWallets(m.client),
	)
}

// Update handles messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if m.filtering {
			switch msg.String() {
			case "enter", "esc":
				m.filtering = false
				return m, nil
			case "backspace":
				if len(m.filter) > 0 {
					m.filter = m.filter[:len(m.filter)-1]
				}
				return m, nil
			default:
				if len(msg.String()) == 1 {
					m.filter += msg.String()
				}
				return m, nil
			}
		}

		switch msg.String() {
		case "q", "ctrl+c":
			m.quitting = true
			return m, tea.Quit
		case "tab", "right", "l":
			m.activeTab = (m.activeTab + 1) % len(tabNames)
			return m, nil
		case "shift+tab", "left", "h":
			m.activeTab = (m.activeTab - 1 + len(tabNames)) % len(tabNames)
			return m, nil
		case "/":
			m.filtering = true
			m.filter = ""
			return m, nil
		case "r":
			m.loading = true
			return m, tea.Batch(
				fetchHealth(m.client),
				fetchAgents(m.client),
				fetchWallets(m.client),
			)
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		return m, nil

	case healthMsg:
		m.health = msg.data
		m.loading = false
		return m, nil

	case agentsMsg:
		m.agents = msg.data
		return m, nil

	case walletsMsg:
		m.wallets = msg.data
		return m, nil

	case errMsg:
		m.err = msg.err
		m.loading = false
		return m, nil
	}

	return m, nil
}

// View renders the dashboard.
func (m Model) View() string {
	if m.quitting {
		return ""
	}

	var b strings.Builder

	// Title
	b.WriteString(StyleTitle.Render("  Sardis Dashboard"))
	b.WriteString("\n")

	// Tabs
	var tabs []string
	for i, name := range tabNames {
		if i == m.activeTab {
			tabs = append(tabs, StyleActiveTab.Render(name))
		} else {
			tabs = append(tabs, StyleTab.Render(name))
		}
	}
	b.WriteString(lipgloss.JoinHorizontal(lipgloss.Top, tabs...))
	b.WriteString("\n\n")

	// Content
	switch m.activeTab {
	case TabOverview:
		b.WriteString(m.renderOverview())
	case TabAgents:
		b.WriteString(m.renderAgents())
	case TabWallets:
		b.WriteString(m.renderWallets())
	case TabTransactions:
		b.WriteString(m.renderTransactions())
	}

	// Filter bar
	if m.filtering {
		b.WriteString(fmt.Sprintf("\n  Filter: %s█", m.filter))
	}

	// Help
	help := "  tab: switch pane • r: refresh • /: filter • q: quit"
	b.WriteString("\n")
	b.WriteString(StyleHelp.Render(help))

	return b.String()
}

func (m Model) renderOverview() string {
	if m.loading {
		return "  Loading..."
	}

	var b strings.Builder
	if m.health != nil {
		if s, ok := m.health["status"].(string); ok {
			style := StyleStatus
			if s != "healthy" {
				style = StyleError
			}
			b.WriteString(fmt.Sprintf("  Platform: %s\n", style.Render(s)))
		}
		if v, ok := m.health["version"].(string); ok {
			b.WriteString(fmt.Sprintf("  Version:  %s\n", v))
		}
		if e, ok := m.health["environment"].(string); ok {
			b.WriteString(fmt.Sprintf("  Env:      %s\n", e))
		}

		// Kill switch
		if components, ok := m.health["components"].(map[string]any); ok {
			if ks, ok := components["kill_switch"].(map[string]any); ok {
				if s, ok := ks["status"].(string); ok {
					style := StyleStatus
					if s == "active" {
						style = StyleError
					}
					b.WriteString(fmt.Sprintf("  Kill SW:  %s\n", style.Render(s)))
				}
			}
		}
	}

	b.WriteString(fmt.Sprintf("\n  Agents:   %d\n", len(m.agents)))
	b.WriteString(fmt.Sprintf("  Wallets:  %d\n", len(m.wallets)))

	return b.String()
}

func (m Model) renderAgents() string {
	if len(m.agents) == 0 {
		return "  No agents found."
	}

	var b strings.Builder
	b.WriteString(StyleTableHeader.Render(fmt.Sprintf("  %-24s %-20s %-12s %-10s", "ID", "NAME", "TYPE", "STATUS")))
	b.WriteString("\n")

	for _, a := range m.agents {
		line := fmt.Sprintf("  %-24s %-20s %-12s %-10s",
			strVal(a, "agent_id"),
			strVal(a, "name"),
			strVal(a, "agent_type"),
			strVal(a, "status"),
		)
		if m.filter != "" && !strings.Contains(strings.ToLower(line), strings.ToLower(m.filter)) {
			continue
		}
		b.WriteString(StyleTableRow.Render(line))
		b.WriteString("\n")
	}

	return b.String()
}

func (m Model) renderWallets() string {
	if len(m.wallets) == 0 {
		return "  No wallets found."
	}

	var b strings.Builder
	b.WriteString(StyleTableHeader.Render(fmt.Sprintf("  %-24s %-24s %-10s %-44s", "ID", "AGENT", "CHAIN", "ADDRESS")))
	b.WriteString("\n")

	for _, w := range m.wallets {
		line := fmt.Sprintf("  %-24s %-24s %-10s %-44s",
			strVal(w, "wallet_id"),
			strVal(w, "agent_id"),
			strVal(w, "chain"),
			strVal(w, "address"),
		)
		if m.filter != "" && !strings.Contains(strings.ToLower(line), strings.ToLower(m.filter)) {
			continue
		}
		b.WriteString(StyleTableRow.Render(line))
		b.WriteString("\n")
	}

	return b.String()
}

func (m Model) renderTransactions() string {
	return "  Transaction view coming soon.\n  Use 'sardis pay' or 'sardis escrow' for now."
}

func strVal(m map[string]any, key string) string {
	if v, ok := m[key].(string); ok && v != "" {
		return v
	}
	return "-"
}

// Fetch commands
func fetchHealth(client *api.Client) tea.Cmd {
	return func() tea.Msg {
		var data map[string]any
		if err := client.Get("/health", &data); err != nil {
			return errMsg{err}
		}
		return healthMsg{data}
	}
}

func fetchAgents(client *api.Client) tea.Cmd {
	return func() tea.Msg {
		var result struct {
			Agents []map[string]any `json:"agents"`
		}
		if err := client.Get("/api/v2/agents", &result); err != nil {
			return errMsg{err}
		}
		return agentsMsg{result.Agents}
	}
}

func fetchWallets(client *api.Client) tea.Cmd {
	return func() tea.Msg {
		var result struct {
			Wallets []map[string]any `json:"wallets"`
		}
		if err := client.Get("/api/v2/wallets", &result); err != nil {
			return errMsg{err}
		}
		return walletsMsg{result.Wallets}
	}
}
