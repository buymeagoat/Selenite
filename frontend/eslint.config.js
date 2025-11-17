import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

// ESLint 8 flat config compatible setup (no 'eslint/config' import)
export default [
  { ignores: ['dist', 'node_modules'] },
  // Base JS and TypeScript recommended configs
  js.configs.recommended,
  ...tseslint.configs.recommended,
  // Project rules
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // React Hooks best practices
      ...(reactHooks.configs.recommended?.rules ?? {}),
      // React Refresh rule to avoid side effects in modules
      'react-refresh/only-export-components': 'warn',
      // Relax TS strictness to align with current codebase
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/ban-ts-comment': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    },
  },
]
