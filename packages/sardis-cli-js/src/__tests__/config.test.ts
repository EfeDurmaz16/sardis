import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { loadConfig, saveConfig, clearCredentials, isSandbox, getConfigPath } from '../config.js';

vi.mock('node:fs', () => ({
  existsSync: vi.fn(),
  readFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  mkdirSync: vi.fn(),
}));

describe('config', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.resetAllMocks();
    process.env = { ...originalEnv };
    delete process.env['SARDIS_API_KEY'];
    delete process.env['SARDIS_API_URL'];
    delete process.env['SARDIS_CHAIN'];
    delete process.env['SARDIS_TOKEN'];
    delete process.env['SARDIS_MODE'];
    delete process.env['SARDIS_AGENT_ID'];
    delete process.env['SARDIS_WALLET_ID'];
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe('loadConfig', () => {
    it('returns defaults when no config file exists', () => {
      vi.mocked(existsSync).mockReturnValue(false);

      const config = loadConfig();
      expect(config.api_key).toBe('');
      expect(config.api_base_url).toBe('https://api.sardis.sh');
      expect(config.default_chain).toBe('base');
      expect(config.default_token).toBe('USDC');
      expect(config.mode).toBe('sandbox');
    });

    it('reads from config file', () => {
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(readFileSync).mockReturnValue(JSON.stringify({
        api_key: 'testkey_123',
        default_chain: 'polygon',
      }));

      const config = loadConfig();
      expect(config.api_key).toBe('testkey_123');
      expect(config.default_chain).toBe('polygon');
      expect(config.default_token).toBe('USDC'); // still default
    });

    it('env vars override file config', () => {
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(readFileSync).mockReturnValue(JSON.stringify({
        api_key: 'testkey_file',
        default_chain: 'polygon',
      }));

      process.env['SARDIS_API_KEY'] = 'testkey_env';
      process.env['SARDIS_CHAIN'] = 'arbitrum';

      const config = loadConfig();
      expect(config.api_key).toBe('testkey_env');
      expect(config.default_chain).toBe('arbitrum');
    });

    it('handles malformed config file', () => {
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(readFileSync).mockReturnValue('not json');

      const config = loadConfig();
      expect(config.api_key).toBe('');
      expect(config.api_base_url).toBe('https://api.sardis.sh');
    });

    it('strips trailing slash from api url', () => {
      process.env['SARDIS_API_URL'] = 'https://api.sardis.sh/';

      vi.mocked(existsSync).mockReturnValue(false);
      const config = loadConfig();
      expect(config.api_base_url).toBe('https://api.sardis.sh');
    });
  });

  describe('saveConfig', () => {
    it('merges with existing config', () => {
      vi.mocked(existsSync).mockReturnValue(true);
      vi.mocked(readFileSync).mockReturnValue(JSON.stringify({
        api_key: 'testkey_existing',
        default_chain: 'base',
      }));

      saveConfig({ default_chain: 'polygon' });

      expect(writeFileSync).toHaveBeenCalledWith(
        expect.stringContaining('config.json'),
        expect.stringContaining('"api_key": "testkey_existing"'),
        'utf-8',
      );
      expect(writeFileSync).toHaveBeenCalledWith(
        expect.any(String),
        expect.stringContaining('"default_chain": "polygon"'),
        'utf-8',
      );
    });

    it('creates config dir if not exists', () => {
      vi.mocked(existsSync).mockReturnValue(false);

      saveConfig({ api_key: 'testkey_new' });

      expect(mkdirSync).toHaveBeenCalledWith(expect.stringContaining('.sardis'), { recursive: true });
    });
  });

  describe('isSandbox', () => {
    it('returns true when no API key', () => {
      expect(isSandbox({ ...loadConfig(), api_key: '' })).toBe(true);
    });

    it('returns true when mode is sandbox', () => {
      expect(isSandbox({ ...loadConfig(), api_key: 'testkey', mode: 'sandbox' })).toBe(true);
    });

    it('returns false when API key is set and mode is live', () => {
      vi.mocked(existsSync).mockReturnValue(false);
      const config = loadConfig();
      expect(isSandbox({ ...config, api_key: 'testkey', mode: 'live' })).toBe(false);
    });
  });

  describe('getConfigPath', () => {
    it('returns path ending with config.json', () => {
      expect(getConfigPath()).toContain('.sardis');
      expect(getConfigPath()).toContain('config.json');
    });
  });
});
