const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '..');

const config = getDefaultConfig(projectRoot);

// Exclude monorepo directories that Metro doesn't need to watch
// This fixes the EMFILE (too many open files) error
config.watchFolders = [projectRoot];

config.resolver.blockList = [
  // Exclude other packages in the monorepo
  new RegExp(`${workspaceRoot}/packages/.*`),
  new RegExp(`${workspaceRoot}/contracts/.*`),
  new RegExp(`${workspaceRoot}/dashboard/.*`),
  new RegExp(`${workspaceRoot}/landing/.*`),
  new RegExp(`${workspaceRoot}/playground/.*`),
  new RegExp(`${workspaceRoot}/examples/.*`),
  new RegExp(`${workspaceRoot}/demos/.*`),
  new RegExp(`${workspaceRoot}/docs/.*`),
  new RegExp(`${workspaceRoot}/scripts/.*`),
  new RegExp(`${workspaceRoot}/marketplace/.*`),
  new RegExp(`${workspaceRoot}/api/.*`),
  new RegExp(`${workspaceRoot}/tests/.*`),
  new RegExp(`${workspaceRoot}/\\.omc/.*`),
  new RegExp(`${workspaceRoot}/\\.claude/.*`),
];

module.exports = config;
