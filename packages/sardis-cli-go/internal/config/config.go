package config

import (
	"os"
	"path/filepath"
)

const (
	DefaultAPIURL = "https://api.sardis.sh"
	ConfigDir     = ".sardis"
	ConfigFile    = "config.yaml"
)

// DefaultConfigPath returns ~/.sardis/
func DefaultConfigPath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return "."
	}
	return filepath.Join(home, ConfigDir)
}

// EnsureConfigDir creates ~/.sardis/ if it doesn't exist.
func EnsureConfigDir() error {
	dir := DefaultConfigPath()
	return os.MkdirAll(dir, 0700)
}
