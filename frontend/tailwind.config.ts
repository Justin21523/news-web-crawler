import type { Config } from "tailwindcss";

const token = (name: string) => `var(${name})`;

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: token("--color-text"),
        "text-secondary": token("--color-text-secondary"),
        muted: token("--color-muted"),
        panel: token("--color-bg"),
        surface: token("--color-surface"),
        "surface-elevated": token("--color-surface-elevated"),
        "surface-muted": token("--color-surface-muted"),
        "surface-subtle": token("--color-surface-subtle"),
        "code-bg": token("--color-code-bg"),
        "code-text": token("--color-code-text"),
        line: token("--color-border"),
        "line-strong": token("--color-border-strong"),
        primary: token("--color-primary"),
        "primary-hover": token("--color-primary-hover"),
        "primary-active": token("--color-primary-active"),
        "primary-dark": token("--color-primary-active"),
        "primary-soft": token("--color-primary-soft"),
        "primary-soft-2": token("--color-primary-soft-2"),
        secondary: token("--color-secondary"),
        "secondary-soft": token("--color-secondary-soft"),
        accent: token("--color-accent"),
        highlight: token("--color-accent"),
        magenta: token("--module-ml"),
        "accent-soft": token("--color-accent-soft"),
        success: token("--semantic-success"),
        "success-soft": token("--semantic-success-soft"),
        "success-border": token("--semantic-success-border"),
        "success-text": token("--semantic-success-text"),
        warn: token("--semantic-warning"),
        "warn-soft": token("--semantic-warning-soft"),
        "warn-border": token("--semantic-warning-border"),
        "warn-text": token("--semantic-warning-text"),
        danger: token("--semantic-error"),
        "danger-soft": token("--semantic-error-soft"),
        "danger-border": token("--semantic-error-border"),
        "danger-text": token("--semantic-error-text"),
        info: token("--semantic-info"),
        "info-soft": token("--semantic-info-soft"),
        "info-border": token("--semantic-info-border"),
        "info-text": token("--semantic-info-text"),
      },
      fontFamily: {
        sans: ["Lato", "Arial", "Helvetica", "sans-serif"],
        mono: ["SFMono-Regular", "Consolas", "Liberation Mono", "monospace"],
      },
      boxShadow: {
        card: "var(--shadow-card)",
        elevated: "var(--shadow-elevated)",
      },
      borderRadius: {
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
      },
    },
  },
  plugins: [],
};

export default config;
