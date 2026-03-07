package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"github.com/sardis-sh/sardis/packages/sardis-cli-go/internal/config"
)

var cfgFile string

// SetVersion sets the CLI version (injected via ldflags).
func SetVersion(v string) {
	rootCmd.Version = v
}

var rootCmd = &cobra.Command{
	Use:   "sardis",
	Short: "Sardis CLI — Payment OS for the Agent Economy",
	Long: `Sardis CLI provides command-line access to the Sardis platform.

Manage agents, wallets, payments, escrows, and kill switches from
your terminal. Use 'sardis dashboard' for an interactive TUI.`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default $HOME/.sardis/config.yaml)")
	rootCmd.PersistentFlags().String("api-url", "", "Sardis API base URL")
	rootCmd.PersistentFlags().String("api-key", "", "API key for authentication")

	_ = viper.BindPFlag("api_url", rootCmd.PersistentFlags().Lookup("api-url"))
	_ = viper.BindPFlag("api_key", rootCmd.PersistentFlags().Lookup("api-key"))
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		cfg := config.DefaultConfigPath()
		viper.AddConfigPath(cfg)
		viper.SetConfigName("config")
		viper.SetConfigType("yaml")
	}

	viper.SetEnvPrefix("SARDIS")
	viper.AutomaticEnv()

	_ = viper.ReadInConfig()
}
