package auth

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/config"
)

// Credentials stores auth tokens on disk.
type Credentials struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	APIKey       string `json:"api_key,omitempty"`
	ExpiresAt    int64  `json:"expires_at"`
	Email        string `json:"email,omitempty"`
	OrgID        string `json:"org_id,omitempty"`
}

const credFile = "credentials.json"

func credPath() string {
	return filepath.Join(config.DefaultConfigPath(), credFile)
}

// Save writes credentials to ~/.sardis/credentials.json.
func Save(creds *Credentials) error {
	if err := config.EnsureConfigDir(); err != nil {
		return err
	}

	data, err := json.MarshalIndent(creds, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(credPath(), data, 0600)
}

// Load reads credentials from disk.
func Load() (*Credentials, error) {
	data, err := os.ReadFile(credPath())
	if err != nil {
		return nil, err
	}

	var creds Credentials
	if err := json.Unmarshal(data, &creds); err != nil {
		return nil, err
	}

	return &creds, nil
}

// IsExpired checks if the access token has expired.
func (c *Credentials) IsExpired() bool {
	return time.Now().Unix() > c.ExpiresAt
}

// Clear removes stored credentials.
func Clear() error {
	return os.Remove(credPath())
}
