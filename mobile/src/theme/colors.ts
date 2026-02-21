export const colors = {
  // Primary Brand Colors
  primary: {
    main: '#7C3AED',      // Deep purple
    light: '#A78BFA',
    dark: '#5B21B6',
    contrast: '#FFFFFF',
  },

  // Accent Colors
  accent: {
    main: '#F59E0B',      // Amber
    light: '#FCD34D',
    dark: '#D97706',
    contrast: '#1F2937',
  },

  // Severity Colors
  severity: {
    info: '#3B82F6',      // Blue
    warning: '#F59E0B',   // Amber
    critical: '#EF4444',  // Red
  },

  // Status Colors
  status: {
    active: '#10B981',    // Green
    paused: '#F59E0B',    // Amber
    blocked: '#EF4444',   // Red
    pending: '#6B7280',   // Gray
  },

  // Semantic Colors
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  info: '#3B82F6',

  // Light Theme
  light: {
    background: '#FFFFFF',
    surface: '#F9FAFB',
    surfaceElevated: '#FFFFFF',
    border: '#E5E7EB',
    text: {
      primary: '#111827',
      secondary: '#6B7280',
      tertiary: '#9CA3AF',
      inverse: '#FFFFFF',
    },
  },

  // Dark Theme
  dark: {
    background: '#111827',
    surface: '#1F2937',
    surfaceElevated: '#374151',
    border: '#374151',
    text: {
      primary: '#F9FAFB',
      secondary: '#D1D5DB',
      tertiary: '#9CA3AF',
      inverse: '#111827',
    },
  },

  // Common
  common: {
    white: '#FFFFFF',
    black: '#000000',
    transparent: 'transparent',
  },
};

export type ColorScheme = 'light' | 'dark';

export const getThemeColors = (scheme: ColorScheme) => ({
  ...colors,
  background: colors[scheme].background,
  surface: colors[scheme].surface,
  surfaceElevated: colors[scheme].surfaceElevated,
  border: colors[scheme].border,
  text: colors[scheme].text,
});
