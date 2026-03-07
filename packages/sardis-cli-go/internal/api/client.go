package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/spf13/viper"

	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/auth"
	"github.com/EfeDurmaz16/sardis/packages/sardis-cli-go/internal/config"
)

// Client is the Sardis API client.
type Client struct {
	BaseURL     string
	APIKey      string
	AccessToken string
	HTTPClient  *http.Client
}

// NewClient creates a Client from viper config and stored credentials.
func NewClient() *Client {
	baseURL := viper.GetString("api_url")
	if baseURL == "" {
		baseURL = config.DefaultAPIURL
	}

	apiKey := viper.GetString("api_key")
	accessToken := ""

	// Load stored credentials if no API key from flags/config
	if creds, err := auth.Load(); err == nil && !creds.IsExpired() {
		if apiKey == "" && creds.APIKey != "" {
			apiKey = creds.APIKey
		}
		if creds.AccessToken != "" {
			accessToken = creds.AccessToken
		}
	}

	return &Client{
		BaseURL:     baseURL,
		APIKey:      apiKey,
		AccessToken: accessToken,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Do sends an HTTP request and decodes the JSON response.
func (c *Client) Do(method, path string, body any, result any) error {
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal request: %w", err)
		}
		bodyReader = bytes.NewReader(data)
	}

	req, err := http.NewRequest(method, c.BaseURL+path, bodyReader)
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if c.APIKey != "" {
		req.Header.Set("X-API-Key", c.APIKey)
	}
	if c.AccessToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.AccessToken)
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(respBody))
	}

	if result != nil {
		if err := json.Unmarshal(respBody, result); err != nil {
			return fmt.Errorf("decode response: %w", err)
		}
	}

	return nil
}

// Get sends a GET request.
func (c *Client) Get(path string, result any) error {
	return c.Do("GET", path, nil, result)
}

// Post sends a POST request.
func (c *Client) Post(path string, body any, result any) error {
	return c.Do("POST", path, body, result)
}

// Delete sends a DELETE request.
func (c *Client) Delete(path string, result any) error {
	return c.Do("DELETE", path, nil, result)
}
