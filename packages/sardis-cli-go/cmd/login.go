package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/pkg/browser"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/auth"
	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/config"
)

var loginCmd = &cobra.Command{
	Use:   "login",
	Short: "Authenticate with Sardis",
	Long:  `Opens a browser for OAuth authentication and stores credentials locally.`,
	RunE:  runLogin,
}

func init() {
	rootCmd.AddCommand(loginCmd)
	loginCmd.Flags().String("email", "", "Email for password-based login")
	loginCmd.Flags().String("password", "", "Password for password-based login")
	loginCmd.Flags().String("key", "", "Authenticate directly with an API key")
}

func runLogin(cmd *cobra.Command, args []string) error {
	apiKey, _ := cmd.Flags().GetString("key")
	if apiKey != "" {
		creds := &auth.Credentials{
			APIKey:    apiKey,
			ExpiresAt: time.Now().Add(365 * 24 * time.Hour).Unix(),
		}
		if err := auth.Save(creds); err != nil {
			return fmt.Errorf("save credentials: %w", err)
		}
		viper.Set("api_key", apiKey)
		fmt.Println("Authenticated with API key.")
		return nil
	}

	email, _ := cmd.Flags().GetString("email")
	password, _ := cmd.Flags().GetString("password")
	if email != "" && password != "" {
		return loginWithPassword(email, password)
	}

	return loginWithBrowser()
}

func loginWithPassword(email, password string) error {
	baseURL := viper.GetString("api_url")
	if baseURL == "" {
		baseURL = config.DefaultAPIURL
	}

	resp, err := http.PostForm(baseURL+"/api/v2/auth/login", url.Values{
		"username": {email},
		"password": {password},
	})
	if err != nil {
		return fmt.Errorf("login request: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != 200 {
		return fmt.Errorf("login failed (%d): %s", resp.StatusCode, string(body))
	}

	var result struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int    `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return fmt.Errorf("parse response: %w", err)
	}

	creds := &auth.Credentials{
		AccessToken: result.AccessToken,
		Email:       email,
		ExpiresAt:   time.Now().Add(time.Duration(result.ExpiresIn) * time.Second).Unix(),
	}
	if err := auth.Save(creds); err != nil {
		return fmt.Errorf("save credentials: %w", err)
	}

	fmt.Printf("Logged in as %s\n", email)
	return nil
}

func loginWithBrowser() error {
	baseURL := viper.GetString("api_url")
	if baseURL == "" {
		baseURL = config.DefaultAPIURL
	}

	authURL := baseURL + "/api/v2/auth/google"
	fmt.Printf("Opening browser for authentication...\n")
	fmt.Printf("If the browser doesn't open, visit: %s\n\n", authURL)

	if err := browser.OpenURL(authURL); err != nil {
		fmt.Printf("Could not open browser: %v\n", err)
		fmt.Printf("Please visit the URL above manually.\n")
	}

	fmt.Println("After authenticating, paste your API key here:")
	fmt.Print("API Key: ")

	var apiKey string
	if _, err := fmt.Scanln(&apiKey); err != nil {
		return fmt.Errorf("read input: %w", err)
	}

	creds := &auth.Credentials{
		APIKey:    apiKey,
		ExpiresAt: time.Now().Add(365 * 24 * time.Hour).Unix(),
	}
	if err := auth.Save(creds); err != nil {
		return fmt.Errorf("save credentials: %w", err)
	}

	fmt.Println("Authenticated successfully.")
	return nil
}
