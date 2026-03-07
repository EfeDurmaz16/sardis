package tui

import "github.com/charmbracelet/lipgloss"

// Sardis brand colors
var (
	ColorPrimary   = lipgloss.Color("#2563EB") // Blue
	ColorSecondary = lipgloss.Color("#7C3AED") // Purple
	ColorSuccess   = lipgloss.Color("#10B981") // Green
	ColorWarning   = lipgloss.Color("#F59E0B") // Amber
	ColorDanger    = lipgloss.Color("#EF4444") // Red
	ColorMuted     = lipgloss.Color("#6B7280") // Gray
	ColorBg        = lipgloss.Color("#111827") // Dark bg
	ColorFg        = lipgloss.Color("#F9FAFB") // Light fg
)

var (
	StyleTitle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorPrimary).
			MarginBottom(1)

	StyleTab = lipgloss.NewStyle().
			Padding(0, 2).
			Foreground(ColorMuted)

	StyleActiveTab = lipgloss.NewStyle().
			Padding(0, 2).
			Bold(true).
			Foreground(ColorPrimary).
			Underline(true)

	StyleStatus = lipgloss.NewStyle().
			Foreground(ColorSuccess)

	StyleError = lipgloss.NewStyle().
			Foreground(ColorDanger)

	StyleHelp = lipgloss.NewStyle().
			Foreground(ColorMuted).
			MarginTop(1)

	StyleTableHeader = lipgloss.NewStyle().
				Bold(true).
				Foreground(ColorPrimary).
				BorderBottom(true).
				BorderStyle(lipgloss.NormalBorder()).
				BorderForeground(ColorMuted)

	StyleTableRow = lipgloss.NewStyle().
			Foreground(ColorFg)

	StyleCard = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(ColorMuted).
			Padding(1, 2)
)
